SNS投稿パイプラインを実行する（Codex用）。

前提: 環境変数 `SNS_PLUGIN_ROOT`（このプラグインの配置先）と `SNS_PIPELINE_HOME`（実データ。未設定なら ~/.sns-pipeline）。

手順:
1. `$SNS_PIPELINE_HOME/config.json` が無ければ未セットアップ。`/sns-setup` を案内して中止。
2. 取込: `SNS_PIPELINE_HOME=$SNS_PIPELINE_HOME python3 "$SNS_PLUGIN_ROOT/engine/ingest.py"` を実行。exit 2=設定未完了で中止、exit 1=エラーで logs を報告し中止、0件でも続行。
3. 取込（バックボーンストック・任意）: `SNS_PIPELINE_HOME=$SNS_PIPELINE_HOME python3 "$SNS_PLUGIN_ROOT/engine/ingest_backbone_stock.py"` を実行。exit 0以外でも本体は止めない。
4. 投稿作成: `"$SNS_PLUGIN_ROOT/engine/compose_prompt.md"` を読み、その手順を最初から最後まで忠実に実行する。テーマごとに `backbone.md`・`image_taste.md`（有効ならバックボーンストックも）を読み、公開済み投稿との整合性チェック（4-4）を経てから、投稿はテーマごとに最大1件、画像は1〜5枚を内容量で判断し過去10枚で同じ骨格を繰り返さない。画像生成は `config.json` の `IMAGE_BACKEND` に従う（自分自身がCodexなら通常 `codex_native`）。`MATERIALS_TABLE_ID` が設定されていれば使用フラグONの素材も参照候補に含める。
5. 報告: 取込件数（テーマ別）/ 分析件数 / 投稿テーマ / 画像枚数 / Baseリンク を簡潔に。

注意: 投稿はBaseの下書き止まり（SNS自動投稿はしない）。画像は画像生成モデル(image_gen)のみで生成し、HTML/スクショ合成はしない。
