SNS投稿パイプラインの初期セットアップ（Codex用）。

前提: 環境変数 `SNS_PLUGIN_ROOT` と `SNS_PIPELINE_HOME`（既定 ~/.sns-pipeline）。テンプレートは `$SNS_PLUGIN_ROOT/templates/`。

手順:
1. `"$SNS_PLUGIN_ROOT/engine/setup_prompt.md"` を読み、その手順に従う。
2. 前提確認（テナント自身の Lark Custom App / lark-cli プロファイル / 対象Baseとbot招待）→ config雛形コピー → 参考元テーブル作成 → テーマ作成（/sns-theme の追加を必要数）→ 拡張機能導入 → 定期実行 → 動作確認。
3. 拡張機能は `$SNS_PLUGIN_ROOT/extension/lark-quick-send/` をChromeに読み込み、各テーマの Webhook URL をオプション画面で登録する。

注意: 開発者（配布元）の資格情報は使わない。各テナントが自分の Lark App・Webhook・Base を使う。既存テーブルがある場合は不足フィールド追加のみ（改名・削除しない）。
