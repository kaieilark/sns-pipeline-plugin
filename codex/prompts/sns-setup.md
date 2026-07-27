SNS投稿パイプラインの初期セットアップ（Codex用）。

前提: 環境変数 `SNS_PLUGIN_ROOT` と `SNS_PIPELINE_HOME`（既定 ~/.sns-pipeline）。テンプレートは `$SNS_PLUGIN_ROOT/templates/`。

手順:
1. `"$SNS_PLUGIN_ROOT/engine/setup_prompt.md"` を読み、その手順に従う。
2. 前提確認（テナント自身の Lark Custom App / lark-cli プロファイル / 対象Baseとbot招待）→ config雛形コピー → **画像生成バックエンドの自動設定（下記・確認不要）** → 参考元テーブル作成 → テーマ作成（/sns-theme の追加を必要数）→ バックボーンストック（任意・§3-2）→ 拡張機能導入 → 定期実行 → 動作確認。
3. **取込元チャットが必要になったタイミングでまだ無い場合は engine/setup_prompt.md §0-5 に従い、対話でチャット作成〜カスタムボットのWebhook発行を案内し、得られた値をその場でconfig.jsonに登録する。** 聞きっぱなしで登録を忘れない。
4. 拡張機能は `$SNS_PLUGIN_ROOT/extension/lark-quick-send/` をChromeに読み込み、各テーマ（＋必要ならバックボーンストック）の Webhook URL をオプション画面で登録する。

画像生成バックエンドの自動設定: このセットアップを実行しているのはCodex自身なので、`engine/setup_prompt.md` §0-6 のとおり**ユーザーに確認せず**、config.jsonの `IMAGE_BACKEND` を `codex_native` に自動設定する（Codex自身のimage_gen機能とサブスクリプションをその場で直接使う。サブプロセスは起動しない）。Claude Code向けの3択（codex_cli/openai_api/custom_script）はここでは提示しない。

注意: 開発者（配布元）の資格情報は使わない。各テナントが自分の Lark App・Webhook・Base を使う。既存テーブルがある場合は不足フィールド追加のみ（改名・削除しない）。バックボーンストックは任意機能。
