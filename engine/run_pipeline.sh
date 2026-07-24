#!/usr/bin/env bash
# SNS投稿パイプライン 定期ラン ラッパー（launchd / cron 用・エージェント非依存）
#
# 役割: 取込(ingest.py) → compose(エージェントに compose_prompt.md を実行させる) の薄いラッパー。
# 実データは SNS_PIPELINE_HOME(既定 ~/.sns-pipeline)。このスクリプト自体は配布物(engine)側。
#
# 環境変数:
#   SNS_PIPELINE_HOME  実データの場所（既定 ~/.sns-pipeline）
#   PYTHON_BIN         python3 実体（既定 python3）
#   AGENT_CMD          compose を実行させるエージェント起動コマンド。
#                      例(Claude Code): 'claude -p'   例(Codex): 'codex exec'
#                      未設定なら compose はスキップし「手動で sns-run を実行してください」と案内する。
set -u

ENGINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${SNS_PIPELINE_HOME:-$HOME/.sns-pipeline}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG_FILE="$HOME_DIR/config.json"
LOG_DIR="$HOME_DIR/logs"
mkdir -p "$LOG_DIR"
STAMP() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(STAMP)] $*" | tee -a "$LOG_DIR/run_$(date +%Y%m%d).log"; }

if [ ! -f "$CONFIG_FILE" ]; then
  log "SETUP-INCOMPLETE: $CONFIG_FILE がありません。setup を先に実行してください。"
  exit 0
fi

# 設定の最低限チェック（BASE_TOKEN / TABLE_ID_SOURCES / 有効な THEMES）
MISSING="$("$PYTHON_BIN" - "$CONFIG_FILE" <<'PYEOF'
import json, sys
try:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    miss = [k for k in ("BASE_TOKEN", "TABLE_ID_SOURCES") if not str(cfg.get(k, "") or "").strip()]
    themes = [t for t in (cfg.get("THEMES") or [])
              if isinstance(t, dict) and t.get("ENABLED") is not False
              and str(t.get("CHAT_ID", "") or "").strip()
              and str(t.get("TABLE_ID_POSTS", "") or "").strip()
              and str(t.get("THEME_KEY", "") or "").strip()]
    if not themes:
        miss.append("THEMES")
    print(" ".join(miss))
except Exception:
    print("CONFIG_UNREADABLE")
PYEOF
)"
if [ -n "$MISSING" ]; then
  log "SETUP-INCOMPLETE: 未設定キー: ${MISSING}。実行をスキップします。"
  exit 0
fi

# 1) 取込
log "取込 (ingest.py) 開始"
SNS_PIPELINE_HOME="$HOME_DIR" "$PYTHON_BIN" "$ENGINE_DIR/ingest.py"
INGEST_RC=$?
log "取込 終了 rc=$INGEST_RC"
if [ "$INGEST_RC" = "2" ]; then
  log "設定未完了のため終了。"; exit 0
fi

# 2) compose（エージェントに指示書を実行させる）
if [ -z "${AGENT_CMD:-}" ]; then
  log "AGENT_CMD 未設定のため compose はスキップ。手動で sns-run（または Codex run プロンプト）を実行してください。"
  exit 0
fi
log "compose 開始 (AGENT_CMD=$AGENT_CMD)"
PROMPT="SNS_PIPELINE_HOME=$HOME_DIR として、$ENGINE_DIR/compose_prompt.md を読み、その手順を最初から最後まで忠実に実行してください。"
SNS_PIPELINE_HOME="$HOME_DIR" $AGENT_CMD "$PROMPT" 2>&1 | tee -a "$LOG_DIR/run_$(date +%Y%m%d).log"
log "compose 終了"
exit 0
