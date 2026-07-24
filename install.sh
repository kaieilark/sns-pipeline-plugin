#!/usr/bin/env bash
# SNS投稿パイプライン プラグイン インストーラ
# Claude Code のスキルと Codex のプロンプトの両方を導入し、ランタイム雛形を用意する。
# 会員データは一切扱わない。実データは SNS_PIPELINE_HOME にユーザーが後から入れる。
set -eu

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${SNS_PIPELINE_HOME:-$HOME/.sns-pipeline}"

echo "== SNS投稿パイプライン インストール =="
echo "plugin root : $PLUGIN_ROOT"
echo "runtime home: $HOME_DIR"

# 1. Claude Code スキル
CLAUDE_SKILLS="$HOME/.claude/skills"
if [ -d "$HOME/.claude" ]; then
  mkdir -p "$CLAUDE_SKILLS"
  for s in sns-run sns-settings sns-theme sns-setup; do
    mkdir -p "$CLAUDE_SKILLS/$s"
    cp "$PLUGIN_ROOT/skills/$s/SKILL.md" "$CLAUDE_SKILLS/$s/SKILL.md"
    # ${CLAUDE_PLUGIN_ROOT} をこのプラグインの実パスに置換（マーケットプレイス未使用の直接導入時）
    sed -i.bak "s#\${CLAUDE_PLUGIN_ROOT}#$PLUGIN_ROOT#g" "$CLAUDE_SKILLS/$s/SKILL.md" && rm -f "$CLAUDE_SKILLS/$s/SKILL.md.bak"
  done
  echo "[OK] Claude Code スキルを $CLAUDE_SKILLS に導入"
else
  echo "[skip] ~/.claude が無いため Claude Code スキルはスキップ"
fi

# 2. Codex プロンプト
CODEX_PROMPTS="$HOME/.codex/prompts"
if [ -d "$HOME/.codex" ]; then
  mkdir -p "$CODEX_PROMPTS"
  for p in sns-run sns-settings sns-theme sns-setup; do
    sed "s#\$SNS_PLUGIN_ROOT#$PLUGIN_ROOT#g" "$PLUGIN_ROOT/codex/prompts/$p.md" > "$CODEX_PROMPTS/$p.md"
  done
  echo "[OK] Codex プロンプトを $CODEX_PROMPTS に導入"
  echo "     （AGENTS.md も併せて参照されます。SNS_PLUGIN_ROOT=$PLUGIN_ROOT を環境に設定すると確実です）"
else
  echo "[skip] ~/.codex が無いため Codex プロンプトはスキップ"
fi

# 3. ランタイム雛形（既存があれば壊さない）
mkdir -p "$HOME_DIR/themes" "$HOME_DIR/logs" "$HOME_DIR/images" "$HOME_DIR/tmp"
if [ ! -f "$HOME_DIR/config.json" ]; then
  cp "$PLUGIN_ROOT/templates/config.example.json" "$HOME_DIR/config.json"
  echo "[OK] $HOME_DIR/config.json を雛形から作成（BASE_TOKEN 等を埋めてください）"
else
  echo "[keep] $HOME_DIR/config.json は既存のため保持"
fi

cat <<EOF

== 次のステップ ==
1. $HOME_DIR/config.json に、テナント自身の PROFILE / BASE_TOKEN 等を設定
2. 初期セットアップ:  Claude Code → /sns-setup   /   Codex → /sns-setup
3. テーマ追加・設定:  /sns-settings（テーマ追加・バックボーン・画像テイスト）
4. 実行:            /sns-run
拡張機能: $PLUGIN_ROOT/extension/lark-quick-send/ を Chrome に読み込み、各テーマの Webhook を登録
EOF
