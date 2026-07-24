#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNS投稿パイプライン - バックボーンストック取込スクリプト (ingest_backbone_stock.py)

概要:
    config.json の BACKBONE_STOCK に定義されたLarkグループチャット
    （経営者・担当者が事業への思い・方針・エピソードを随時書き溜めるチャット）の
    新着メッセージを差分取得し、バックボーンストックテーブル(Lark Base)にレコード化する。
    ingest.py（素材案テーブル向け）とは完全に独立したテーブル・状態を持つ。
    全テーマ共通（テーマの区別をしない）。

    これは THEMES[].BACKBONE_FILE（テーマ別・静的なMarkdown、いつでも書き換え可能）とは
    別物。BACKBONE_STOCK は時系列で積み上がっていく生のメモ・語りで、
    compose_prompt.md の本文作成時にテーマを問わず全件参照する「解釈のレンズ」として使う
    （参考元の要約が本文の主材料であることは変わらない。バックボーンストックは素材の代替ではない）。

ランタイムの場所:
    SNS_PIPELINE_HOME 環境変数(未設定なら ~/.sns-pipeline)。

依存:
    - Python 3 標準ライブラリのみ
    - lark-cli (Base書込は PROFILE / --as bot、チャット読取は CHAT_PROFILE / --as user)

取込対象:
    - ingest.py と同様、送信者が人間かbot連携かを問わずテキスト/postメッセージを取込対象とする。
    - 系統・種別・URL・要約などの分類は行わない（素材案テーブルとは別物・生ログとして貯める）。

冪等性:
    - state.json の backbone_stock.last_create_time_ms / backbone_stock.processed_message_ids
      で ingest.py の themes.* とは独立に管理する。
    - message_id による重複判定で二重取込を防止。

終了コード:
    0: 正常終了(新着なしを含む)
    1: 実行エラー
    2: 設定未完了、または BACKBONE_STOCK.ENABLED=false（致命的ではない。
       このスクリプトの失敗・スキップでパイプライン全体を止めてはならない。
       呼び出し側 run_pipeline.sh は本スクリプトの exit code を無視して継続する）
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

# バックボーンストックテーブルのフィールド名(schema.backbone_stock.json と同一名・変更禁止)
FIELDS = [
    "タイトル",
    "元テキスト",
    "投稿者名",
    "メッセージ投稿日時",
    "取込日時",
    "取込元メッセージID",
]

TITLE_LEN = 40
BATCH_LIMIT = 200
MAX_PAGES = 200
CLI_TIMEOUT_SEC = 120

log = logging.getLogger("ingest_backbone_stock")


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOG_DIR / ("ingest_backbone_stock_%s.log" % datetime.now().strftime("%Y%m%d"))
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
    bb = cfg.get("BACKBONE_STOCK") or {}
    if bb.get("ENABLED") is not True:
        log.info("BACKBONE_STOCK.ENABLED が true でないため終了します（未使用の機能。エラーではない）")
        sys.exit(2)
    missing = [k for k in ("CHAT_ID", "TABLE_ID") if not str(bb.get(k, "")).strip()]
    if missing or not str(cfg.get("BASE_TOKEN", "")).strip():
        log.error("未設定: BACKBONE_STOCK.%s が config.json で空です。", " / ".join(missing) or "BASE_TOKEN")
        sys.exit(2)
    return cfg, bb


def load_state():
    state = {}
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("state.json の読込に失敗したため初期状態で継続します: %s", e)
            state = {}
    bb_state = state.setdefault("backbone_stock", {})
    bb_state.setdefault("last_create_time_ms", 0)
    bb_state.setdefault("processed_message_ids", [])
    return state, bb_state


def save_state(state, keep):
    bb = state.get("backbone_stock", {})
    bb["processed_message_ids"] = bb.get("processed_message_ids", [])[-keep:]
    state["last_saved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tmp = STATE_PATH.with_name(STATE_PATH.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


_PROFILE_DEFAULT = object()


def run_lark_cli(cfg, args, profile=_PROFILE_DEFAULT):
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
        raise RuntimeError(
            "lark-cli 異常終了 rc=%d stderr=%s stdout=%s"
            % (proc.returncode, proc.stderr.strip()[:500], proc.stdout.strip()[:500])
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("lark-cli 出力のJSON解析に失敗: %s" % proc.stdout.strip()[:500])
    code = payload.get("code") if isinstance(payload, dict) else None
    if code not in (None, 0):
        raise RuntimeError("Lark APIエラー code=%s msg=%s" % (code, payload.get("msg")))
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
    送信者が人間・アプリを問わず対象とする(ingest.py と同方針)。"""
    if msg.get("deleted"):
        return False
    if msg.get("msg_type") not in ("text", "post"):
        return False
    return True


def _walk_post(node, texts):
    if isinstance(node, dict):
        tag = node.get("tag")
        if tag in ("text", "a", "md") and node.get("text"):
            texts.append(str(node["text"]))
        for v in node.values():
            if isinstance(v, (list, dict)):
                _walk_post(v, texts)
    elif isinstance(node, list):
        for v in node:
            _walk_post(v, texts)


def extract_text(msg):
    body = msg.get("body") or {}
    raw = body.get("content") or msg.get("content") or ""
    if not isinstance(raw, str):
        raw = json.dumps(raw, ensure_ascii=False) if raw else ""
    try:
        content = json.loads(raw)
    except json.JSONDecodeError:
        content = None

    if msg.get("msg_type") == "text":
        text = content.get("text", "") or raw if isinstance(content, dict) else raw
    else:  # post
        if isinstance(content, (dict, list)):
            texts = []
            _walk_post(content, texts)
            title = content.get("title") if isinstance(content, dict) else ""
            parts = ([title] if title else []) + texts
            text = "\n".join(p for p in parts if p) or raw
        else:
            text = raw

    for m in msg.get("mentions") or []:
        key, name = m.get("key"), m.get("name")
        if key and name:
            text = text.replace(key, "@" + name)
    return text.strip()


def build_record(msg, cfg, now_str):
    text = extract_text(msg)
    if not text:
        return None
    title = re.sub(r"\s+", " ", text).strip()[:TITLE_LEN] or "(無題)"

    sender = msg.get("sender") or {}
    sender_id = str(sender.get("id") or "")
    name_map = cfg.get("SENDER_NAME_MAP") or {}
    sender_name = name_map.get(sender_id) or sender_id or "(不明)"

    ct_ms = create_time_ms(msg)
    msg_dt = (
        datetime.fromtimestamp(ct_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
        if ct_ms > 0 else None
    )

    return {
        "message_id": str(msg.get("message_id") or ""),
        "row": [
            title,              # タイトル
            text,               # 元テキスト
            sender_name,        # 投稿者名
            msg_dt,             # メッセージ投稿日時
            now_str,            # 取込日時
            str(msg.get("message_id") or ""),  # 取込元メッセージID
        ],
    }


def fetch_messages(cfg, bb, st):
    chat_profile = str(cfg.get("CHAT_PROFILE", "") or "") or None
    base_args = [
        "im", "+chat-messages-list",
        "--chat-id", bb["CHAT_ID"],
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
        log.info("初回ラン: 過去 %d 日分を取得対象とします", lookback)
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
        log.info("ページ %d: %d 件取得 (has_more=%s)", page, len(items), has_more)
        if not has_more or not page_token:
            break
    else:
        log.warning("ページ上限(%d)に到達。残りは次回ランで取得します", MAX_PAGES)

    messages.sort(key=create_time_ms)
    return messages


def write_chunk(cfg, bb, chunk):
    body = {"fields": FIELDS, "rows": [r["row"] for r in chunk]}
    args = [
        "base", "+record-batch-create",
        "--base-token", str(cfg["BASE_TOKEN"]),
        "--table-id", str(bb["TABLE_ID"]),
        "--as", "bot",
        "--json", json.dumps(body, ensure_ascii=False),
        "--format", "json",
    ]
    run_lark_cli(cfg, args)


def main():
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging()
    log.info("=== バックボーンストック取込ラン開始 ===")

    cfg, bb = load_config()
    state, st = load_state()
    keep = int(cfg.get("PROCESSED_ID_KEEP", 2000))
    log.info("対象チャット: %s (%s)", bb.get("CHAT_NAME", ""), bb["CHAT_ID"])

    try:
        messages = fetch_messages(cfg, bb, st)
    except RuntimeError as e:
        log.error("メッセージ取得に失敗: %s", e)
        return 1

    if not messages:
        log.info("新着メッセージはありません")
        save_state(state, keep)
        return 0

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
        rec = build_record(msg, cfg, now_str)
        if rec is None:
            skipped_other += 1
            continue
        new_records.append(rec)
        processed.add(mid)

    log.info(
        "取得 %d 件 / 新規 %d 件 / 処理済みスキップ %d 件 / 対象外 %d 件",
        len(messages), len(new_records), skipped_dup, skipped_other,
    )

    if not new_records:
        st["last_create_time_ms"] = max(int(st["last_create_time_ms"]), fetched_max_ms)
        log.info("書込対象なし(watermarkのみ更新)")
        save_state(state, keep)
        return 0

    written_ids = []
    failed = False
    try:
        for i in range(0, len(new_records), BATCH_LIMIT):
            chunk = new_records[i:i + BATCH_LIMIT]
            write_chunk(cfg, bb, chunk)
            written_ids.extend(r["message_id"] for r in chunk)
            log.info("レコード書込: %d 件 (累計 %d / %d)", len(chunk), len(written_ids), len(new_records))
    except RuntimeError as e:
        log.error("レコード書込に失敗: %s", e)
        failed = True

    st["processed_message_ids"].extend(written_ids)
    if not failed:
        st["last_create_time_ms"] = max(int(st["last_create_time_ms"]), fetched_max_ms)
    save_state(state, keep)
    log.info("=== 取込ラン完了: 合計 %d 件を書き込みました%s ===",
             len(written_ids), "（失敗あり）" if failed else "")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
