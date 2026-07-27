SNS投稿パイプラインのテーマ管理（Codex用）。

前提: 環境変数 `SNS_PLUGIN_ROOT` と `SNS_PIPELINE_HOME`（既定 ~/.sns-pipeline）。テンプレートは `$SNS_PLUGIN_ROOT/templates/`。

手順:
1. `"$SNS_PLUGIN_ROOT/engine/theme_prompt.md"` を読み、その手順に従う。
2. 操作を選ぶ: 一覧(A) / 追加(B) / バックボーン設定(C) / 画像テイスト設定(D) / 編集・停止・再開(E)。
3. 追加(B)では、`CHAT_ID` が未確定なら engine/setup_prompt.md §0-5（チャット作成ガイド）を先に対話で実行し、得られた値を登録してから、テーママスターへレコード作成（`THEME_RECORD_ID`取得） → テーマ専用の投稿管理テーブル作成 → テーマ用フォルダ scaffold（backbone/image_taste/design_framework_log）→ config.THEMES 追記、まで行う。

注意: テーマはテーママスター（正規化された1テーブル）に1レコードずつ存在し、素材案テーブルはそこへリンクして全テーマ共通の1つ、投稿管理テーブルはテーマごとに別。単一選択(select)の選択肢追加操作はしない。テーブル・レコードの物理削除はしない（削除は ENABLED:false）。`lark-cli base --help` で正確なサブコマンド名を確認してから実行。
