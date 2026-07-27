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

## 0-6. 画像生成バックエンドの選択（`IMAGE_BACKEND`・省略禁止）

> 投稿画像（手順5・`compose_prompt.md` §5）は必ず画像生成モデルで作る。しかし**実行中のエージェント自身が画像生成モデルを持っているとは限らない**（Claude Codeは持たない）。どう生成するかを `config.json` の `IMAGE_BACKEND` に明示的に設定してから先へ進む。

### 選べる4つのバックエンド

| 値 | 説明 | 必要なもの |
|---|---|---|
| `codex_native` | **実行中のエージェント自身がCodex** の場合に使う。Codex自身の image_gen 機能をその場で直接使う（サブプロセスを起動しない）。 | 追加設定不要（Codexのサブスクリプションで完結） |
| `codex_cli` | 実行中のエージェントは別（例: Claude Code）だが、**別途インストール済みの `codex` CLI** をサブプロセスとして呼び出す（`codex exec ...`）。既存の compose_prompt.md §5-1 はこの前提で書かれている。 | `codex` CLI が使える環境・Codexのサブスクリプション |
| `openai_api` | **OpenAI Images API を従量課金で直接**呼び出す。Codex CLIを使わない。 | `IMAGE_BACKEND_CONFIG.OPENAI_API_KEY_ENV` に指定した環境変数にAPIキーを設定 |
| `custom_script` | その他の画像生成API/ツールをラップした**自作スクリプト**を呼び出す。 | `IMAGE_BACKEND_CONFIG.CUSTOM_SCRIPT_PATH`（下記の契約を満たすスクリプト） |

### 選び方（このセットアップを実行しているエージェント自身が判断する。ここが本手順の核）

- **今この手順を実行しているのが Codex 自身の場合** → **ユーザーに確認せず、自動的に `codex_native` を設定する。** Codexは自分自身の画像生成能力とサブスクリプションをそのまま使えるため、選択の必要がない。
- **今この手順を実行しているのが Claude Code（またはその他、画像生成モデルを持たないエージェント）の場合** → **必ずユーザーに次の3択を尋ねる**（黙って `codex_cli` を既定にしない）:
  1. 「Codex CLIのサブスクリプションを使う」（`codex_cli`・**推奨・既定の案内として提示してよい**。別途 `codex` コマンドが必要）
  2. 「OpenAI API等の従量課金APIを使う」（`openai_api`。APIキーの用意が必要）
  3. 「その他のAPI/ツールを自分で用意する」（`custom_script`。契約は下記）
  選ばれた値を `config.json` の `IMAGE_BACKEND` に書き込む。`openai_api` ならAPIキーの環境変数名を確認（既定 `OPENAI_API_KEY`）し `IMAGE_BACKEND_CONFIG.OPENAI_API_KEY_ENV` に設定、`custom_script` ならスクリプトの絶対パスを `IMAGE_BACKEND_CONFIG.CUSTOM_SCRIPT_PATH` に設定する。

### `custom_script` の契約（自作スクリプトを使う場合）

呼び出し規約（compose_prompt.md 側がこの規約で呼ぶ）:
```bash
<CUSTOM_SCRIPT_PATH> --prompt-file <生成指示テキストのファイルパス> --aspect-ratio 4:5 --out <出力先PNGの絶対パス>
```
- スクリプトは指定された `--out` パスに画像ファイル（PNG）を生成して正常終了（exit 0）すること。失敗時は非0で終了する。
- 複数枚必要な場合は、compose_prompt.md 側がページごとに1回ずつこのスクリプトを呼ぶ（スクリプト自身が複数ファイルを一括生成する必要はない）。

### 後から変更する場合
`/sns-settings` →「画像生成バックエンドを変更する」で、いつでも選び直せる。

## 1. ランタイムの用意
```bash
mkdir -p $HOME_DIR/{themes,logs,images,tmp}
cp $TPL/config.example.json $HOME_DIR/config.json   # 既存があれば上書きしない。無い時だけコピー
```
- `config.json` の `PROFILE`（Base書込プロファイル）・`CHAT_PROFILE`（チャット読取。空=デフォルト）・`BASE_TOKEN` を、このテナントの値で埋める。
- `BASE_TOKEN` は、wikiノードURLしか無い場合 `lark-cli base +url-resolve`（または `docs`/`wiki` 系の解決コマンド）で token を得る。

## 2. テーママスター・参考元テーブルの作成

> **順序が重要**: 参考元テーブルの「テーマリンク」フィールドはテーママスターへリンクするため、
> 先にテーママスターを作り、その `table_id` を使って参考元テーブルを作る。

1. **テーママスターテーブルを作成する**:
   `lark-cli base --help` で `+table-create` の綴りを確認してから、`$TPL/schema.theme_master.json` の `fields` を渡して作成する:
   `lark-cli --profile <PROFILE> base +table-create --base-token <BASE_TOKEN> --json '<schema.theme_master.json 相当>' --as bot`
   返った `table_id` を config の `THEME_MASTER_TABLE_ID` に書く。
2. **「共通」レコードを1件作成する**（テーマを問わず使う素材ライブラリのレコード等が参照する固定レコード）:
   `lark-cli --profile <PROFILE> base +record-create --base-token <BASE_TOKEN> --table-id <THEME_MASTER_TABLE_ID> --json '{"fields":{"NAME":"共通","THEME_KEY":"","DESCRIPTION":"テーマを問わず使う汎用データ向け（例: ロゴ等の素材）"}}' --as bot`
   返った `record_id` を config の `SHARED_THEME_RECORD_ID` に書く。
3. **参考元テーブルを作成する**: `$TPL/schema.sources.json` を読み、`テーマリンク` フィールドの `link_table` の `__THEME_MASTER_TABLE_ID__` を手順1で得た `THEME_MASTER_TABLE_ID` に置換してから作成する:
   `lark-cli --profile <PROFILE> base +table-create --base-token <BASE_TOKEN> --json '<置換後のJSON>' --as bot`
   返った `table_id` を config の `TABLE_ID_SOURCES` に書く。
4. **「テーマ」フィールドが実際に formula として機能するか確認する**: `+field-list` でフィールド一覧を取得し、「テーマリンク」（link）と「テーマ」（formula）の両方が存在することを確認する。可能であれば1件テストレコードを作成し（「テーマリンク」に手順2の共通レコードのrecord_idを設定）、「テーマ」フィールドに `共通` が正しく表示されるか、`+record-list --filter-json` で「テーマ」を条件にした絞り込みが効くかを確認してからテストレコードを削除する。formulaがフィルタ・グループ化で正しく機能しない版のLark Base/lark-cliに当たった場合は、`テーマ`フィールドの式（`FIRST([テーマリンク].[NAME])`）を見直すか、運用側に制約（フィルタは「テーマリンク」の record_id で行う等）を明記する。

## 3. テーマの作成（1つ以上）
- **テーマ管理指示書 `theme_prompt.md` の B（追加）** を、必要なテーマ数だけ実行する。
  各テーマで、テーママスターへのレコード作成（`THEME_RECORD_ID`）・投稿管理テーブル作成（`TABLE_ID_POSTS`）・テーマ用フォルダ（backbone/image_taste/rotation log）が用意される。
  **`CHAT_ID` が未確定なら、着手前に手順0-5（チャットが存在しない場合の作成ガイド）を実行する。**
- 続けて各テーマの **バックボーン（C）** と **画像テイスト（D）** を設定する。

## 3-2. バックボーンストックの設定（任意機能・全テーマ共通）

「時系列で書き溜める思い・方針を、テーマを問わず全投稿のレンズとして使いたい」場合に設定する。**必須ではない**（設定しなくてもテーマ別の `BACKBONE_FILE` と参考元の要約だけで本文作成は成立する）。導入するか、ユーザーに尋ねてから進める。

導入する場合:
1. `config.json` の `BACKBONE_STOCK.CHAT_ID` が未確定なら、**手順0-5（チャットが存在しない場合の作成ガイド）を実行する**（チャット名の例:「バックボーンストック」「思考ログ」等）。
2. テーブルを作成する: `$TPL/schema.backbone_stock.json` の `fields` を渡し、
   `lark-cli --profile <PROFILE> base +table-create --base-token <BASE_TOKEN> --json '<schema.backbone_stock.json 相当>' --as bot` を実行。返った `table_id` を `BACKBONE_STOCK.TABLE_ID` に書く。
   - **固定（プライマリ）フィールドは「ID」（auto_number）にする。「タイトル」等の内容依存フィールドを固定にしない。** 理由: Lark Base は固定フィールドをあとから変更できない。テーブルが未使用（0件）の新規作成時は、この原則を最初から満たす設計にできる（既にデータがある既存テーブルへの応急処置＝内容にプレフィックスを足す等とは状況が違う。新規テーブルでは応急処置に頼らず正しい設計を選ぶ）。
   - `auto_number` / `user`（「投稿者名」）の正確な type 文字列は、実行前に `lark-cli base --help` 系のfield-create仕様（版により綴りが変わることがある）で確認してから作成する。
3. `BACKBONE_STOCK.ENABLED` を `true` にする。
4. `engine/ingest_backbone_stock.py` を1回手動実行し、正常終了すること（0件でもよい）を確認する。実データがある場合は、Lark Base画面で「投稿者名」が実在ユーザーの名前・アイコンとして正しく表示されているか目視確認する。
5. 以後は `run_pipeline.sh`（Step 1b）または `sns-run` の一部として自動で取り込まれる。中身は人がチャットに随時書き込むだけでよく、レコードを直接編集する運用ではない。

> **この設計原則（固定フィールドを内容依存にしない・関連者情報はuser型で持つ）は、バックボーンストック以外の新規テーブルを作る際にも適用する。** 新しいテーブルを設計するたびに、固定フィールドの型・内容が本当に最善かを一度立ち止まって検討してから `+table-create` を実行すること。

## 3-3. 素材ライブラリの設定（任意機能）

画像生成のたびに使い回したい既定の参照画像（店舗オーナー写真・ロゴ等）を、Base側で管理したい場合に設定する。**必須ではない**（設定しなくても `THEMES[].LOGO_FILE` と `IMAGE_TASTE_FILE` の `MODE=image` 参照画像だけで画像生成は成立する）。

導入する場合:
1. テーブルを作成する: `$TPL/schema.materials.json` を読み、「テーマリンク」の `link_table` の `__THEME_MASTER_TABLE_ID__` を `THEME_MASTER_TABLE_ID`（§2で作成済み）に置換してから作成する:
   `lark-cli --profile <PROFILE> base +table-create --base-token <BASE_TOKEN> --json '<置換後のJSON>' --as bot` を実行。返った `table_id` を config の `MATERIALS_TABLE_ID` に書く。
2. **運用は人がBase画面で直接レコードを追加する**（自動取込スクリプトは無い）。1レコード=1素材。「タイトル」（例: 店舗オーナー写真）・「画像」（添付）・「備考」（この素材が何で、画像生成時にどう扱ってよいか。例:「店舗オーナーです。服装の変更は許可します」）・「テーマリンク」（対象テーマ、または特定テーマに紐付かない場合は§2の共通レコード）・「使用フラグ」（ONの素材だけが画像生成の参照候補になる）を人に入力してもらう。
3. `config.json` の `MATERIALS_TABLE_ID` が空でなければ、`compose_prompt.md` の画像生成手順が自動でこのテーブルを参照する（そのテーマ、または共通にリンクし使用フラグ=trueの素材を取得し、参照画像として渡し、備考の文言をプロンプトに反映する）。

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
- `THEME_MASTER_TABLE_ID` / `TABLE_ID_SOURCES` と各テーマの `TABLE_ID_POSTS` について `+field-list` を実行し、
  スキーマ（schema.theme_master.json / schema.sources.json / schema.posts.json）と突き合わせて過不足を報告する。
- `BACKBONE_STOCK.ENABLED` が true なら `BACKBONE_STOCK.TABLE_ID` についても同様に `schema.backbone_stock.json` と突き合わせる。
- `MATERIALS_TABLE_ID` が空でなければ同様に `schema.materials.json` と突き合わせる。
- テーママスターに「共通」レコード（`SHARED_THEME_RECORD_ID` の指す record）が実在するか確認する。
- **不足フィールドの追加のみ**行い、既存フィールドの改名・削除はしない。テーブルが未作成なら作成する。
