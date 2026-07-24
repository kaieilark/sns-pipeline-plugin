---
name: sns-run
description: SNS投稿パイプラインを実行する。テーマ別チャットに集めた素材案（URL/コメント）を取込→要約→Instagram/Threads/X本文→参考画像→テーマ別の投稿管理テーブルへ登録する。今すぐ投稿案を作りたいときに使う。
---

# sns-run — SNS投稿パイプライン実行

このプラグインの生成エンジンを、現セッションで即時実行する。

## 手順
1. ランタイムの場所を決める: `SNS_PIPELINE_HOME`（未設定なら `~/.sns-pipeline`）。`config.json` が無ければ未セットアップなので `sns-setup` を案内して中止。
2. **取込**: `SNS_PIPELINE_HOME=<home> python3 "${CLAUDE_PLUGIN_ROOT}/engine/ingest.py"` を実行する。
   - exit 2 = 設定未完了（中止・報告）。exit 1 = いずれかのテーマで取得/書込エラー（logs を報告して中止）。取込0件でも続行。
3. **投稿作成**: `"${CLAUDE_PLUGIN_ROOT}/engine/compose_prompt.md"` を読み、その手順（絶対ルール含む）を忠実に実行する。
   - 各テーマの `backbone.md`（背景・思想）と `image_taste.md`（画像テイスト）を読んでから本文・画像を作る。
   - 投稿は**テーマごとに最大1件**。テーマが違う投稿を同じ方針・同じ画像テイストで作らない。
   - 画像は**過去10枚で同じ骨格（フレームワークA〜J）を繰り返さない**（テーマ別の `design_framework_log.json` で管理）。
4. **報告**: 取込件数（テーマ別）/ 分析件数 / 投稿テーマ（テーマ名とタイトル）/ 画像枚数 / Baseリンク を簡潔に報告する。

## 注意
- Lark: チャット読取=読取用プロファイル(--as user) / Base書込=書込用プロファイル(--as bot)。config の値に従う。
- 投稿はBaseの下書き止まり。SNSへの自動投稿はしない。
- `${CLAUDE_PLUGIN_ROOT}` はこのプラグインの配置先。Codex で使う場合は engine ファイルの絶対パスに読み替える。
