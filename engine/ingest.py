#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNS投稿パイプライン - チャット差分取込スクリプト (ingest.py)

概要:
    config.json の THEMES に定義された各Larkグループチャットの新着メッセージを
    差分取得し、参考元テーブル(Lark Base・全テーマ共通)にレコード化する。
    取込元チャット(CHAT_ID)でテーマが一意に決まるため、レコードの「テーマ」フィールドへ
    自動で書き込む。投稿(記事)側はテーマごとに別テーブルだが、素材案はこの1テーブルに集約する。
    launchd/cron による定期ラン(1日1回程度)から呼ばれる前提。常時イベント監視はしない。

ランタイムの場所:
    SNS_PIPELINE_HOME 環境変数(未設定なら ~/.sns-pipeline)。ここに config.json / state.json を置く。
    このスクリプト自体は配布物(プラグイン)側にあり、実データはランタイム側にある。

依存:
    - Python 3 標準ライブラリのみ
    - lark-cli (Base書込はテナントのプロファイル PROFILE / --as bot、チャット読取は CHAT_PROFILE / --as user)

取込対象:
    - チャットに投稿されたテキスト/postメッセージは、送信者が人間かbot連携(アプリ経由投稿)かを
      問わず取込対象とする(is_target 参照)。送信者種別で絞ると、bot連携で投稿された内容が
      無条件に取りこぼされるため、この絞り込みはしない。
    - 1メッセージ = 1参考元候補として扱う。時間的に近接した複数メッセージ(例: URL投稿の直後に
      別メッセージが続く等)を、内容を確認せず同一の話題として統合してはならない
      (compose 側の絶対ルールでも明記。ingest.py はメッセージ単位でレコードを分離する設計を保つ)。

冪等性:
    - state.json の themes.<THEME_KEY> に最終処理済み create_time(ms) と処理済み message_id(直近N件)を保持
    - message_id による重複判定で二重取込を防止
    - 書込失敗時はそのテーマの watermark を進めず終了する(次回ランで再取得、書込済みIDはスキップ)

終了コード:
    0: 正常終了(新着なしを含む)
    1: 実行エラー(1テーマでも失敗すれば1)
    2: 設定未完了(BASE_TOKEN / TABLE_ID_SOURCES / THEMES が未設定)
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME_DIR = Path(os.environ.get("SNS_PIPELINE_HOME", str(Path.home() / ".sns-pipeline")))
CONFIG_PATH = HOME_DIR / "config.json"
STATE_PATH = HOME_DIR / "state.json"
LOG_DIR = HOME_DIR / "logs"

# 参考元テーブルのフィールド名(schema.sources.json と同一名・変更禁止)
FIELDS = [
    "タイトル",
    "種別",
    "テーマ",
    "URL",
    "元テキスト",
    "分析ステータス",
    "取込元メッセージID",
    "投稿者名",
    "メッセージ投稿日時",
    "取込日時",
    "使用状況",
]

KIND_URL = "URL記事"
KIND_COMMENT = "コメント"
STATUS_UNANALYZED = "未分析"
USAGE_UNUSED = "未使用"

URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")
TITLE_LEN = 30
BATCH_LIMIT = 200
MAX_PAGES = 200
CLI_TIMEOUT_SEC = 120

log = logging.getLogger("ingest")


# ---------------------------------------------------------------- 基盤

def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOG_DIR / ("ingest_%s.log" % datetime.now().strftime("%Y%m%d"))
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.setLevel(logging.INFO)
    log.addHandler(fh)
    log.addHandler(sh)


def load_config():
    if not CONFIG_PATH.exists():
        log.error("config.json が見つかりません: %s", CONFIG_PATH)
        sys.exit(2)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error("config.json の読込に失敗: %s", e)
        sys.exit(2)
    missing = [k for k in ("BASE_TOKEN", "TABLE_ID_SOURCES") if not str(cfg.get(k, "")).strip()]
    if missing:
        log.error("未設定: %s が config.json で空です。", " / ".join(missing))
        sys.exit(2)
    themes = load_themes(cfg)
    if not themes:
        log.error("未設定: config.json の THEMES に有効な取込元チャットがありません。")
        sys.exit(2)
    return cfg, themes


def load_themes(cfg):
    """config.json の THEMES を正規化して返す。"""
    themes = []
    for t in cfg.get("THEMES") or []:
        if not isinstance(t, dict) or t.get("ENABLED") is False:
            continue
        key = str(t.get("THEME_KEY", "") or "").strip()
        chat_id = str(t.get("CHAT_ID", "") or "").strip()
        name = str(t.get("NAME", "") or "").strip()
        if not (key and chat_id and name):
            log.warning("THEMES の要素をスキップ(THEME_KEY/CHAT_ID/NAME のいずれかが空): %s", t)
            continue
        themes.append({
            "key": key,
            "name": name,
            "chat_id": chat_id,
            "display": str(t.get("CHAT_NAME", "") or chat_id),
        })
    return themes


def load_state(themes):
    state = {}
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("state.json の読込に失敗したため初期状態で継続します: %s", e)
            state = {}
    state.setdefault("themes", {})
    for t in themes:
        st = state["themes"].setdefault(t["key"], {})
        st.setdefault("last_create_time_ms", 0)
        st.setdefault("processed_message_ids", [])
    return state


def save_state(state, keep):
    for st in state.get("themes", {}).values():
        st["processed_message_ids"] = st.get("processed_message_ids", [])[-keep:]
    state["last_saved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tmp = STATE_PATH.with_name(STATE_PATH.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


_PROFILE_DEFAULT = object()


def run_lark_cli(cfg, args, profile=_PROFILE_DEFAULT):
    """lark-cli を実行し JSON を返す。profile 省略時=cfg.PROFILE(Base書込)。None=デフォルト(チャット読取)。"""
    if profile is _PROFILE_DEFAULT:
        profile = str(cfg.get("PROFILE", "") or "")
    cmd = ["lark-cli"] + (["--profile", profile] if profile else []) + args
    log.info("lark-cli 実行: %s", " ".join(a if len(a) < 120 else a[:117] + "..." for a in cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT_SEC)
    except FileNotFoundError:
        raise RuntimeError("lark-cli が見つかりません。PATH を確認してください。")
    except subprocess.TimeoutExpired:
        raise RuntimeError("lark-cli が %d 秒でタイムアウトしました。" % CLI_TIMEOUT_SEC)
    if proc.returncode != 0:
        raise RuntimeError("lark-cli 異常終了 rc=%d stderr=%s stdout=%s"
                           % (proc.returncode, proc.stderr.strip()[:500], proc.stdout.strip()[:500]))
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("lark-cli 出力のJSON解析に失敗: %s" % proc.stdout.strip()[:500])
    code = payload.get("code") if isinstance(payload, dict) else None
    if code not in (None, 0):
        raise RuntimeError("Lark APIエラー code=%s msg=%s (スコープ未付与の可能性: im:message:readonly / bitable書込)"
                           % (code, payload.get("msg")))
    return payload


def extract_page(payload):
    if isinstance(payload, list):
        return payload, False, ""
    if not isinstance(payload, dict):
        return [], False, ""
    data = payload.get("data", payload)
    if isinstance(data, list):
        return data, False, ""
    if not isinstance(data, dict):
        return [], False, ""
    items = data.get("items") or data.get("messages") or []
    return items, bool(data.get("has_more")), str(data.get("page_token") or "")


# ---------------------------------------------------------------- 取得

def fetch_messages(cfg, theme, st):
    chat_profile = str(cfg.get("CHAT_PROFILE", "") or "") or None
    base_args = [
        "im", "+chat-messages-list",
        "--chat-id", theme["chat_id"],
        "--as", str(cfg.get("CHAT_IDENTITY", "user")),
        "--order", "asc",
        "--page-size", str(cfg.get("PAGE_SIZE", 50)),
        "--no-reactions",
        "--format", "json",
    ]
    last_ms = int(st.get("last_create_time_ms") or 0)
    if last_ms > 0:
        start_dt = datetime.fromtimestamp(last_ms // 1000, tz=timezone.utc)
    else:
        lookback = int(cfg.get("INITIAL_LOOKBACK_DAYS", 30))
        start_dt = datetime.now(timezone.utc) - timedelta(days=lookback)
        log.info("[%s] 初回ラン: 過去 %d 日分を取得対象とします", theme["key"], lookback)
    base_args += ["--start", start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")]

    messages = []
    page_token = ""
    for page in range(1, MAX_PAGES + 1):
        args = list(base_args)
        if page_token:
            args += ["--page-token", page_token]
        payload = run_lark_cli(cfg, args, profile=chat_profile)
        items, has_more, page_token = extract_page(payload)
        messages.extend(m for m in items if isinstance(m, dict))
        log.info("[%s] ページ %d: %d 件取得 (has_more=%s)", theme["key"], page, len(items), has_more)
        if not has_more or not page_token:
            break
    else:
        log.warning("[%s] ページ上限(%d)に到達。残りは次回ランで取得します", theme["key"], MAX_PAGES)

    messages.sort(key=create_time_ms)
    return messages


# ---------------------------------------------------------------- 解析

def create_time_ms(msg):
    raw = msg.get("create_time")
    if raw is None:
        return 0
    s = str(raw).strip()
    if s.isdigit():
        return int(s)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return int(datetime.strptime(s, fmt).timestamp() * 1000)
        except ValueError:
            continue
    return 0


def is_target(msg):
    """取込対象メッセージか判定(システム・非テキスト系のみ除外)。
    チャットに投稿された内容は送信者が人間・アプリ(bot連携等)を問わず参考元候補とする。
    かつて sender_type=="user" に限定していたが、bot連携で投稿された内容が
    無条件に取りこぼされる問題があったため撤廃した(教訓: 発信者を絞らず、
    テキスト/postメッセージであることだけを条件にする)。"""
    if msg.get("deleted"):
        return False
    if msg.get("msg_type") not in ("text", "post"):
        return False
    return True


def _walk_post(node, texts, urls):
    if isinstance(node, dict):
        tag = node.get("tag")
        if tag in ("text", "a", "md") and node.get("text"):
            texts.append(str(node["text"]))
        if tag == "a" and node.get("href"):
            urls.append(str(node["href"]))
        for v in node.values():
            if isinstance(v, (list, dict)):
                _walk_post(v, texts, urls)
    elif isinstance(node, list):
        for v in node:
            _walk_post(v, texts, urls)


def extract_text(msg):
    body = msg.get("body") or {}
    raw = body.get("content") or msg.get("content") or ""
    if not isinstance(raw, str):
        raw = json.dumps(raw, ensure_ascii=False) if raw else ""
    try:
        content = json.loads(raw)
    except json.JSONDecodeError:
        content = None

    urls = []
    if msg.get("msg_type") == "text":
        text = content.get("text", "") or raw if isinstance(content, dict) else raw
    else:
        if isinstance(content, (dict, list)):
            texts = []
            _walk_post(content, texts, urls)
            title = content.get("title") if isinstance(content, dict) else ""
            parts = ([title] if title else []) + texts
            text = "\n".join(p for p in parts if p) or raw
        else:
            text = raw

    for m in msg.get("mentions") or []:
        key, name = m.get("key"), m.get("name")
        if key and name:
            text = text.replace(key, "@" + name)
    return text.strip(), urls


def build_record(msg, cfg, now_str, theme_name):
    text, post_urls = extract_text(msg)
    if not text and not post_urls:
        return None

    found = URL_RE.findall(text)
    all_urls = found + [u for u in post_urls if u not in found]
    url = all_urls[0].rstrip(".,、。") if all_urls else None
    kind = KIND_URL if url else KIND_COMMENT

    title_src = re.sub(r"\s+", " ", text).strip() or (url or "")
    title = title_src[:TITLE_LEN] or "(無題)"

    sender = msg.get("sender") or {}
    sender_id = str(sender.get("id") or "")
    name_map = cfg.get("SENDER_NAME_MAP") or {}
    sender_name = name_map.get(sender_id) or sender_id or "(不明)"

    ct_ms = create_time_ms(msg)
    msg_dt = datetime.fromtimestamp(ct_ms / 1000).strftime("%Y-%m-%d %H:%M:%S") if ct_ms > 0 else None

    return {
        "message_id": str(msg.get("message_id") or ""),
        "row": [
            title,               # タイトル
            kind,                # 種別
            theme_name,          # テーマ
            url,                 # URL
            text,                # 元テキスト
            STATUS_UNANALYZED,   # 分析ステータス
            str(msg.get("message_id") or ""),  # 取込元メッセージID
            sender_name,         # 投稿者名
            msg_dt,              # メッセージ投稿日時
            now_str,             # 取込日時
            USAGE_UNUSED,        # 使用状況
        ],
    }


# ---------------------------------------------------------------- 冪等性の再構築

def _collect_message_ids(node, out):
    if isinstance(node, str):
        if node.startswith("om_"):
            out.add(node)
    elif isinstance(node, dict):
        for v in node.values():
            _collect_message_ids(v, out)
    elif isinstance(node, list):
        for v in node:
            _collect_message_ids(v, out)


def rebuild_processed_from_base(cfg):
    ids = set()
    limit = 200
    for page in range(MAX_PAGES):
        args = [
            "base", "+record-list",
            "--base-token", str(cfg["BASE_TOKEN"]),
            "--table-id", str(cfg["TABLE_ID_SOURCES"]),
            "--field-id", "取込元メッセージID",
            "--limit", str(limit),
            "--offset", str(page * limit),
            "--as", "bot",
            "--format", "json",
        ]
        try:
            payload = run_lark_cli(cfg, args)
        except RuntimeError as e:
            log.warning("Base側の既存メッセージID再構築に失敗(そのまま継続): %s", e)
            break
        items, has_more, _ = extract_page(payload)
        _collect_message_ids(payload, ids)
        if len(items) < limit and not has_more:
            break
    log.info("Base側から既存メッセージID %d 件を再構築しました", len(ids))
    return ids


# ---------------------------------------------------------------- 書込

def write_chunk(cfg, chunk):
    body = {"fields": FIELDS, "rows": [r["row"] for r in chunk]}
    args = [
        "base", "+record-batch-create",
        "--base-token", str(cfg["BASE_TOKEN"]),
        "--table-id", str(cfg["TABLE_ID_SOURCES"]),
        "--as", "bot",
        "--json", json.dumps(body, ensure_ascii=False),
        "--format", "json",
    ]
    run_lark_cli(cfg, args)


# ---------------------------------------------------------------- テーマ単位取込

def ingest_theme(cfg, theme, st, base_message_ids):
    key, name = theme["key"], theme["name"]
    log.info("--- [%s] %s / %s 取込開始 ---", key, name, theme["display"])

    if base_message_ids is not None and not st.get("processed_message_ids"):
        st["processed_message_ids"] = sorted(base_message_ids)

    try:
        messages = fetch_messages(cfg, theme, st)
    except RuntimeError as e:
        log.error("[%s] メッセージ取得に失敗: %s", key, e)
        return 0, True

    if not messages:
        log.info("[%s] 新着メッセージはありません", key)
        return 0, False

    fetched_max_ms = max(create_time_ms(m) for m in messages)
    processed = set(st["processed_message_ids"])
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_records = []
    skipped_dup = 0
    skipped_other = 0
    for msg in messages:
        mid = str(msg.get("message_id") or "")
        if not mid or mid in processed:
            skipped_dup += 1
            continue
        if not is_target(msg):
            skipped_other += 1
            continue
        rec = build_record(msg, cfg, now_str, name)
        if rec is None:
            skipped_other += 1
            continue
        new_records.append(rec)
        processed.add(mid)

    log.info("[%s] 取得 %d 件 / 新規 %d 件 / 処理済みスキップ %d 件 / 対象外 %d 件",
             key, len(messages), len(new_records), skipped_dup, skipped_other)

    if not new_records:
        st["last_create_time_ms"] = max(int(st["last_create_time_ms"]), fetched_max_ms)
        log.info("[%s] 書込対象なし(watermarkのみ更新)", key)
        return 0, False

    written_ids = []
    try:
        for i in range(0, len(new_records), BATCH_LIMIT):
            chunk = new_records[i:i + BATCH_LIMIT]
            write_chunk(cfg, chunk)
            written_ids.extend(r["message_id"] for r in chunk)
            log.info("[%s] レコード書込: %d 件 (累計 %d / %d)",
                     key, len(chunk), len(written_ids), len(new_records))
    except RuntimeError as e:
        log.error("[%s] レコード書込に失敗: %s", key, e)
        st["processed_message_ids"].extend(written_ids)
        return len(written_ids), True

    st["processed_message_ids"].extend(written_ids)
    st["last_create_time_ms"] = max(int(st["last_create_time_ms"]), fetched_max_ms)
    return len(written_ids), False


# ---------------------------------------------------------------- メイン

def main():
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging()
    log.info("=== チャット差分取込ラン開始 (home=%s) ===", HOME_DIR)

    cfg, themes = load_config()
    state_existed = STATE_PATH.exists()
    state = load_state(themes)
    keep = int(cfg.get("PROCESSED_ID_KEEP", 500))
    log.info("対象テーマ: %s", " / ".join("%s(%s)" % (t["key"], t["name"]) for t in themes))

    needs_rebuild = (not state_existed) or any(
        not state["themes"][t["key"]]["processed_message_ids"]
        and not state["themes"][t["key"]]["last_create_time_ms"]
        for t in themes
    )
    base_message_ids = rebuild_processed_from_base(cfg) if needs_rebuild else None

    total_written = 0
    failed = False
    for theme in themes:
        written, err = ingest_theme(cfg, theme, state["themes"][theme["key"]], base_message_ids)
        total_written += written
        failed = failed or err

    save_state(state, keep)
    log.info("=== 取込ラン完了: 合計 %d 件を書き込みました%s ===",
             total_written, "（一部テーマで失敗あり）" if failed else "")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
