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

## 0-5. チャットが存在しない場合の作成ガイド（テーマ追加・バックボーンストック設定で共通利用・省略禁止）

> **CHAT_ID が必要になるたびに（テーマ追加＝手順3、バックボーンストック＝手順3-2）、このサブ手順を実行する。**
> 「チャットが既にある前提」で黙って進めず、**必ず対話で確認 → 無ければ作成を案内 → 得られた値をその場で config.json に登録**、まで一連で行う。値を聞きっぱなしにして登録を忘れない。

1. **まずユーザーに尋ねる**: 「このテーマ（またはバックボーンストック）用の取込元チャットは、Larkに既にありますか？ あれば、チャット名かLarkの共有リンクを教えてください。無ければ、これから作成する手順を案内します。」
2. **無い場合、チャット作成を案内する**:
   - Lark クライアントで新しいグループチャットを作成してもらう（名前の例: 「〇〇用-SNS案」「バックボーンストック」等、用途がわかる名前を提案する）。
   - **チャット読取用アカウント（`CHAT_PROFILE`/`CHAT_IDENTITY=user` に対応する、いま lark-cli にログインしているユーザー本人）を、そのチャットのメンバーに入れてもらう。** 読取はこのユーザー識別で行うため、メンバーでないとメッセージが取得できない。
   - Bot をこのチャットのメンバーに入れる必要は無い（Base への書込は Bot が行うが、チャット自体への参加は不要）。
3. **カスタムボットで Webhook URL を発行してもらう**（素材投入の Chrome拡張機能や将来の通知連携に使う）:
   - Lark クライアントでそのチャットを開く → チャット設定（グループ設定）→ ボット（Bots）→ 「カスタムボットを追加（Add a Custom Bot）」→ Webhook URL が発行される。
   - 発行された Webhook URL をそのままコピーしてもらい、**セッション内で貼ってもらう**。
4. **CHAT_ID を解決する**。次のいずれかで得る:
   - 読取用プロファイルでチャット名検索: `lark-cli im +chat-search --query "<チャット名>" --as <cfg.CHAT_IDENTITY>`（`--profile <cfg.CHAT_PROFILE>` を付ける。空なら省略）。結果からユーザーに該当のチャットを確認してもらう。
   - 検索でヒットしない・複数候補で迷う場合は、ユーザーにそのチャットの Lark 共有リンク（`...open?openChatId=oc_xxxxxxxx...` の形式）を貼ってもらい、`openChatId` の値を CHAT_ID として使う。
5. **得られた CHAT_ID と WEBHOOK_URL を、その場で config.json に書き込む**（テーマ追加なら該当テーマの `CHAT_ID`/`WEBHOOK_URL`、バックボーンストックなら `BACKBONE_STOCK.CHAT_ID`/`WEBHOOK_URL`）。**聞いた値を確認だけして登録し忘れることを禁止する。**
6. 登録後、実際に読めるか1回テストする: `lark-cli --profile <cfg.CHAT_PROFILE or空> im +chat-messages-list --chat-id <CHAT_ID> --as <cfg.CHAT_IDENTITY> --page-size 1 --format json`。エラーなら手順2（メンバー招待漏れ）を再確認する。

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
  **`CHAT_ID` が未確定なら、着手前に手順0-5（チャットが存在しない場合の作成ガイド）を実行する。**
- 続けて各テーマの **バックボーン（C）** と **画像テイスト（D）** を設定する。

## 3-2. バックボーンストックの設定（任意機能・全テーマ共通）

「時系列で書き溜める思い・方針を、テーマを問わず全投稿のレンズとして使いたい」場合に設定する。**必須ではない**（設定しなくてもテーマ別の `BACKBONE_FILE` と参考元の要約だけで本文作成は成立する）。導入するか、ユーザーに尋ねてから進める。

導入する場合:
1. `config.json` の `BACKBONE_STOCK.CHAT_ID` が未確定なら、**手順0-5（チャットが存在しない場合の作成ガイド）を実行する**（チャット名の例:「バックボーンストック」「思考ログ」等）。
2. テーブルを作成する: `$TPL/schema.backbone_stock.json` の `fields` を渡し、
   `lark-cli --profile <PROFILE> base +table-create --base-token <BASE_TOKEN> --json '<schema.backbone_stock.json 相当>' --as bot` を実行。返った `table_id` を `BACKBONE_STOCK.TABLE_ID` に書く。
3. `BACKBONE_STOCK.ENABLED` を `true` にする。
4. `engine/ingest_backbone_stock.py` を1回手動実行し、正常終了すること（0件でもよい）を確認する。
5. 以後は `run_pipeline.sh`（Step 1b）または `sns-run` の一部として自動で取り込まれる。中身は人がチャットに随時書き込むだけでよく、レコードを直接編集する運用ではない。

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
- `BACKBONE_STOCK.ENABLED` が true なら `BACKBONE_STOCK.TABLE_ID` についても同様に `schema.backbone_stock.json` と突き合わせる。
- **不足フィールドの追加のみ**行い、既存フィールドの改名・削除はしない。テーブルが未作成なら作成する。
