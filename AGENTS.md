# AGENTS.md — SNS投稿パイプライン プラグイン

このリポジトリは、Larkチャットに集めた素材から、テーマ別にSNS投稿の下書き（Instagram/Threads/X本文＋参考画像）を
作り、Lark Baseへ蓄積する配布用パイプライン。**Claude Code と Codex の両方で使える。**

## エージェント別の使い方

- **Claude Code**: `skills/` の各スキル（`sns-run` / `sns-settings` / `sns-theme` / `sns-setup`）を使う。
  `install.sh` で `~/.claude/skills/` に導入するか、プラグインとしてマーケットプレイス経由で入れる。
- **Codex**: `codex/prompts/` の各プロンプト（同名）を `~/.codex/prompts/` に置いて `/sns-run` 等で呼ぶ。
  `install.sh` が導入する。`SNS_PLUGIN_ROOT` にこのリポジトリの絶対パスを設定しておくこと。

どちらのエージェントでも、実際のロジックは `engine/` に集約されている（下記）。エージェントは薄い入口から
engine の指示書を読んで実行するだけ。実データ（config・テーマ定義・状態）は `SNS_PIPELINE_HOME`
（既定 `~/.sns-pipeline`）に置き、このリポジトリには入れない。

## engine（ロジックの正本）
- `engine/ingest.py` … テーマ別チャットの差分取込（素材案テーブルへ・全テーマ共通の1テーブル、テーマ振り分け付き）
- `engine/ingest_backbone_stock.py` … バックボーンストック（継続蓄積・全テーマ共通・任意機能）の差分取込
- `engine/compose_prompt.md` … 要約→本文3種→公開整合性チェック→参考画像→テーマ別投稿管理テーブルへ登録
- `engine/theme_prompt.md` … テーマの追加・編集・一覧・停止/再開
- `engine/settings_prompt.md` … 統括設定メニュー（テーマ追加・バックボーン修正・画像テイスト変更・バックボーンストック 等）
- `engine/setup_prompt.md` … 新テナントの初期セットアップ（§0-5にチャット作成ガイドを内蔵）
- `engine/run_pipeline.sh` … launchd/cron 用の薄いラッパー（AGENT_CMD にエージェント起動コマンドを渡す）

## 設計の要点（必ず守る）
- **テーマ複数対応**: 「会社ブランディング用」「募集用」のように投稿系統を分ける。テーマは config の `THEMES` に足すだけで増える。
- **テーブル分割**: 投稿（記事）はテーマごとに別テーブル（`TABLE_ID_POSTS`）。素材案はチャットIDで振り分くので全テーマ共通の1テーブル（`TABLE_ID_SOURCES`）でよい。
- **バックボーン（背景・思想）**: テーマごとに `themes/<key>/backbone.md`。HPのURL / 直接入力 / 資料ファイル から作れ、後からいつでも変更可能。
- **バックボーンストック（継続蓄積・任意機能）**: `BACKBONE_STOCK` で設定する、テーマを問わず共通の「時系列で書き溜める思い・方針」チャット。`themes/<key>/backbone.md`（いつでも書き換え可能な背景設定シート）とは別物で、混同しない。本文作成時に全件参照するが、素材の要約の代わりにはしない（解釈のレンズとして使う）。
- **画像テイスト**: テーマごとに `themes/<key>/image_taste.md`。Instagram等のURL / 画像添付 / 説明文 で指定でき、後から変更可能。
- **画像の重複回避**: 直近10枚で同じ骨格（フレームワークA〜J）を繰り返さない。ローテーションはテーマ別に `themes/<key>/design_framework_log.json` で管理する。
- **画像枚数**: 1〜5枚を内容の情報量で判断する（固定既定を置かない。過去の枚数傾向も理由にしない）。
- **記事方針**: 全テーマ共通で「読み手の教育 → 問い合わせへの誘導」（気づき→教育→橋渡し→誘導）。本文にURLは貼らず「プロフィールのリンクから」で誘導。**本文作成前に、そのテーマの公開済み投稿と矛盾しないか確認する**（compose_prompt.md 4-4）。
- **画像は画像生成モデルのみ**で文字・ロゴまで描く（HTML/CSS/SVG/スクショ合成は禁止）。
- **チャットが無い場合**: テーマ追加・バックボーンストック設定で取込元チャットが未確定なら、対話でチャット作成〜カスタムボットのWebhook発行を案内し、得られた値をその場で config.json に登録する（`engine/setup_prompt.md` §0-5。聞きっぱなしで登録を忘れない）。
- **配布物に会員データを入れない**: BASE_TOKEN・チャットID・Webhook・実バックボーン・実ロゴはランタイム側（`SNS_PIPELINE_HOME`）にのみ置く。

## 素材投入の拡張機能
`extension/lark-quick-send/`（Chrome拡張・Manifest V3）。Webページの選択テキスト/リンクを右クリックから
テーマ別Larkチャットへ送る。Webhook URL はブラウザにローカル保存（配布物にハードコードしない）。
