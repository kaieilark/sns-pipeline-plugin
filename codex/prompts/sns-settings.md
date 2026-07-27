SNS投稿パイプラインの統括設定メニュー（Codex用）。

前提: 環境変数 `SNS_PLUGIN_ROOT` と `SNS_PIPELINE_HOME`（既定 ~/.sns-pipeline）。

手順:
1. `"$SNS_PLUGIN_ROOT/engine/settings_prompt.md"` を読み、その手順に従う。**専門用語を知らない利用者向けに、選んだ項目を平易な言葉で説明してから作業する**（engine/setup_prompt.md §0-1 対話の進め方・用語集に従う）。
2. `$SNS_PIPELINE_HOME/config.json` を読み現状を要約する。無ければ `/sns-setup` を案内。
3. 選択肢を提示して選んでもらう: テーマ追加 / テーマ一覧・編集 / バックボーン修正 / 画像テイスト変更 / ロゴ設定 / 誘導先・読者・ゴール変更 / テーブル構成確認・再作成 / 設定一覧表示 / 拡張機能の導入手順 / バックボーンストック（継続蓄積）の設定・確認 / 画像生成バックエンドの変更 / 素材ライブラリの設定・確認。
4. 選ばれた項目に応じ `engine/theme_prompt.md` または `engine/setup_prompt.md` の該当セクションを実行する。**取込元チャットが未確定なら engine/setup_prompt.md §0-5（チャット作成ガイド）を対話で実行し、得られた値をその場でconfig.jsonに登録する。** **画像生成バックエンドの変更では、実行している自分自身がCodexなので `codex_native` を確認なしで設定してよい。**
5. 変更後、何を変えたか・次回ランから反映されることを短く報告。

注意: 秘匿情報（BASE_TOKEN・WEBHOOK_URL 等）は表示時マスク。既存レコード・テーブルは壊さない。
