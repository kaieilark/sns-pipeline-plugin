# 初期セットアップ 指示書（setup step・エージェント共通）

新しいテナント（他社）で、このSNS投稿パイプラインを使えるようにする。
ランタイムは `SNS_PIPELINE_HOME`（未設定なら `~/.sns-pipeline`）配下（以降 `$HOME_DIR`）。
配布物側テンプレートは、このファイルと同じ階層の `../templates/`（以降 `$TPL`）と `./`（engine）にある。

> **前提**: このテナント自身の Lark Custom App（Bot）が用意され、lark-cli のプロファイルが作られていること。
> 開発者（配布元）の資格情報は使わない。各テナントが自分の資格情報を入れる。

## 0. 前提の確認
- `lark-cli --version` と、Base書込用プロファイル（`--as bot`）・チャット読取用（`--as user`）が使えることを確認する。
- 対象 Base（Lark Bitable）が用意され、Bot が編集権限で招待されていることを確認する。無ければ、
  Base をユーザーに作ってもらい、Bot をコラボレーターに追加してもらう（Bot 自身では Base を作らない運用を推奨）。

## 1. ランタイムの用意
```bash
mkdir -p $HOME_DIR/{themes,logs,images,tmp}
cp $TPL/config.example.json $HOME_DIR/config.json   # 既存があれば上書きしない。無い時だけコピー
```
- `config.json` の `PROFILE`（Base書込プロファイル）・`CHAT_PROFILE`（チャット読取。空=デフォルト）・`BASE_TOKEN` を、このテナントの値で埋める。
- `BASE_TOKEN` は、wikiノードURLしか無い場合 `lark-cli base +url-resolve`（または `docs`/`wiki` 系の解決コマンド）で token を得る。

## 2. 参考元テーブル（全テーマ共通）の作成
- `lark-cli base --help` で `+table-create` の綴りを確認する。
- `$TPL/schema.sources.json` の `fields` を渡してテーブルを作成する:
  `lark-cli --profile <PROFILE> base +table-create --base-token <BASE_TOKEN> --json '<schema.sources.json 相当>' --as bot`
  - 「テーマ」フィールドの options は空でよい（テーマ追加時に NAME を足していく）。
- 返った `table_id` を config の `TABLE_ID_SOURCES` に書く。

## 3. テーマの作成（1つ以上）
- **テーマ管理指示書 `theme_prompt.md` の B（追加）** を、必要なテーマ数だけ実行する。
  各テーマで投稿管理テーブルが作られ、`TABLE_ID_POSTS`・「テーマ」選択肢・テーマ用フォルダ（backbone/image_taste/rotation log）が用意される。
- 続けて各テーマの **バックボーン（C）** と **画像テイスト（D）** を設定する。

## 4. 素材投入の導線（Lark クイック送信 拡張機能）
「参考にしたい記事URLやコメントを、Larkのテーマ別チャットに集める」導線を用意する。手軽にするための Chrome 拡張機能を同梱している。
- 場所: 配布物の `extension/lark-quick-send/`。
- 導入: Chrome → 拡張機能 → デベロッパーモードON → 「パッケージ化されていない拡張機能を読み込む」で `extension/lark-quick-send/` を選ぶ。
- 設定: 拡張機能のオプション画面で、各テーマの取込元チャットに紐づく **Lark カスタムボットの Webhook URL** を登録する（テーマごとに1つ）。
  - Webhook は各チャットで「設定 → ボット → カスタムボットを追加」で発行する（テナント側で行う）。
- これで、Webページ上の選択テキストやリンクを右クリック →「Lark クイック送信」で、対象テーマのチャットへ投げ込める。
- **拡張機能に会員データは含まれない**（Webhook はブラウザにローカル保存され、配布物にはハードコードしない）。

## 5. 定期実行（任意）
- 手動: `sns-run`（Codexなら run プロンプト）を叩けば、その場で取込→投稿作成まで走る。
- 自動: `engine/run_pipeline.sh` を launchd（macOS）や cron で1日1回程度呼ぶ。`SNS_PIPELINE_HOME` を環境変数で渡す。
  - run_pipeline.sh は取込（ingest.py）→ compose（compose_prompt.md をエージェントに実行させる）→ 後片付けの薄いラッパー。
  - 実行エージェント（claude / codex）は環境に合わせて選ぶ。

## 6. 動作確認
- テーマ別チャットに素材を1件投げてから `sns-run` を実行し、
  参考元テーブルに「テーマ」付きで1件入る → 要約 → 該当テーマの投稿管理テーブルに本文3種＋画像が入る、まで通ることを確認する。
- 生成物はBaseの下書き。SNSへの自動投稿はしない（人が確認して投稿する）。

## テーブル構成の確認・再作成（settings の 7 から呼ばれる）
- `TABLE_ID_SOURCES` と各テーマの `TABLE_ID_POSTS` について `+field-list` を実行し、
  スキーマ（schema.sources.json / schema.posts.json）と突き合わせて過不足を報告する。
- **不足フィールドの追加のみ**行い、既存フィールドの改名・削除はしない。テーブルが未作成なら作成する。
