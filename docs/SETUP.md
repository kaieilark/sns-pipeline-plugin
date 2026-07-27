# セットアップ手順（テナント向け）

このパイプラインを自社で使うための手順。エンジンの詳細な挙動は `engine/*.md` を参照。

## 0. 前提

- **Lark Custom App（Bot）** を自社テナントで作成し、`lark-cli` のプロファイルを用意する。
  - Base 書込用（`--as bot`）と、チャット読取用（`--as user`）が使えること。
  - 必要スコープ: メッセージ読取（`im:message:readonly`）と Bitable の読み書き。
- 投稿を貯める **Lark Base（Bitable）** を用意し、上記 Bot を編集権限で招待する。
- Python 3 と `lark-cli` がインストール済みであること。

## 1. インストール

```bash
git clone <this private repo> ~/sns-pipeline-plugin
cd ~/sns-pipeline-plugin
./install.sh
```

`install.sh` は Claude Code スキル（`~/.claude/skills/`）と Codex プロンプト（`~/.codex/prompts/`）を導入し、
ランタイム `~/.sns-pipeline/`（`SNS_PIPELINE_HOME` で変更可）に `config.json` 雛形を用意する。

## 2. config.json を埋める

`~/.sns-pipeline/config.json`:
- `PROFILE`: Base 書込用の lark-cli プロファイル名
- `CHAT_PROFILE`: チャット読取用（空＝デフォルトプロファイル）
- `BASE_TOKEN`: 対象 Base のトークン
- `TABLE_ID_SOURCES`: 後述の参考元テーブル作成後に自動で入る（手動でもよい）
- `THEMES`: テーマ定義（後述。`/sns-theme` で追加すると自動で書かれる）
- `IMAGE_BACKEND` / `IMAGE_BACKEND_CONFIG`: 画像生成の実行方法（次項）

### 2-1. 画像生成バックエンドを選ぶ（Claude Code実行時は必須）

Claude Code自身は画像生成モデルを持たないため、`/sns-setup` の中で必ず選ぶことになる（`engine/setup_prompt.md` §0-6）:

| 選択肢 | `IMAGE_BACKEND` の値 | 必要なもの |
|---|---|---|
| Codex CLIのサブスクリプションを使う（推奨） | `codex_cli` | 別途 `codex` コマンドが使える環境 |
| OpenAI API等の従量課金APIを使う | `openai_api` | APIキー（環境変数に設定） |
| 自作スクリプトで他のAPI/ツールを使う | `custom_script` | 契約を満たすスクリプト（§0-6参照） |

**Codex自身にこのプラグインを導入した場合は、確認なしで自動的に `codex_native`**（Codex自身のimage_gen機能をその場で直接使う）に設定される。

後から `/sns-settings` →「画像生成バックエンドを変更する」でいつでも切り替えられる。

## 3. テーブルを作る

`/sns-setup`（Codexも同名）を実行すると、指示書 `engine/setup_prompt.md` に沿って:
- **テーママスターテーブル** を作成 → `THEME_MASTER_TABLE_ID` に記録。「共通」レコードを1件作り `SHARED_THEME_RECORD_ID` に記録。
- **参考元テーブル（全テーマ共通）** をテーママスターへリンクする形で作成 → `TABLE_ID_SOURCES` に記録
- テーマごとに **投稿管理テーブル** を作成（`/sns-theme` の追加で）→ 各 `TABLE_ID_POSTS` に記録

> テーブル分割の考え方: **作成する記事（投稿）はテーマごとに別テーブル**。素材案はチャットIDで
> 振り分けられるので**全テーマ共通の1テーブル**でよい。
>
> **「テーマ」は正規化されたマスターテーブルで管理する**（単一選択(select)の重複ではなく、テーママスター1つ＋各テーブルからの「テーマリンク」＋formula）。同じ選択肢を参考元・素材ライブラリなど複数テーブルに重複させると、テーマの追加・改名のたびに同期漏れが起きやすいため。テーマの追加・改名は、テーママスター側の1レコードを直すだけで全体に反映される。

## 4. テーマを設定する

`/sns-settings` → 「テーマを追加する」。各テーマで:
- `NAME`（表示名）/ `CHAT_ID`（素材を集めるチャット）/ `READER`（読者）/ `GOAL`（ゴール）/ `CTA_URL`（誘導先）
- テーママスターへレコードが作成され、`THEME_RECORD_ID` が自動で記録される（参考元テーブルへの書込に使う）。
- **バックボーン**（背景・思想）: HPのURL / 直接入力 / 資料ファイル から作る（`themes/<key>/backbone.md`）。後から変更可。
- **画像テイスト**: Instagram URL / 画像添付 / 説明文（`themes/<key>/image_taste.md`）。後から変更可。
- **ロゴ**（任意）: 画像に必ず入れるロゴを登録（`LOGO_FILE`）。

### 4-1. 取込元チャットがまだ無い場合（対話で作成〜登録まで案内される）

`CHAT_ID` を聞かれた際「まだ無い」と答えると、エージェントが以下を対話で案内する（`engine/setup_prompt.md` §0-5）。**この流れは飛ばさず、最後に config.json への登録まで行われる。**

1. Larkでグループチャットを新規作成する（例:「〇〇用-SNS案」）。
2. **チャット読取用アカウント**（`CHAT_PROFILE`/`CHAT_IDENTITY=user` に対応する、lark-cliにログイン中のユーザー本人）を、そのチャットのメンバーに入れる。Bot自身は入れなくてよい（メッセージ読取はユーザー識別で行うため）。
3. チャット設定 → ボット（Bots）→「カスタムボットを追加」→ 発行された **Webhook URL** をコピーし、エージェントに伝える。
4. エージェントがチャット名検索、またはあなたが貼った共有リンク（`...open?openChatId=oc_xxxxxxxx...`）から `CHAT_ID` を解決する。
5. 得られた `CHAT_ID` と `WEBHOOK_URL` は、その場で config.json（該当テーマ、またはバックボーンストック）に書き込まれる。

同じ流れは、後述のバックボーンストック（4-2）でも共通で使う。

### 4-2. バックボーンストック（継続蓄積・任意機能）

特定のチャットに随時書き溜められる「事業への思い・方針・エピソード」を、テーマを問わず本文作成のレンズとして自動参照させたい場合に設定する。**必須ではない**（無くてもテーマ別バックボーンと素材の要約だけで本文作成は成立する）。

`/sns-settings` → 「バックボーンストックを設定・確認する」。チャットが無ければ 4-1 と同じ流れで作成〜登録し、専用テーブル（`schema.backbone_stock.json`）を作成、`BACKBONE_STOCK.ENABLED` を `true` にする。以後は自動取込される（`themes/<key>/backbone.md` とは別物・詳細は `AGENTS.md`）。

### 4-3. 素材ライブラリ（任意機能）

画像生成のたびに使い回したい既定の参照画像（店舗オーナー写真・ロゴ等）をBaseで管理したい場合に設定する。**必須ではない**（無くても `LOGO_FILE` と画像テイストの参照画像だけで画像生成は成立する）。

`/sns-settings` → 「素材ライブラリを設定・確認する」。テーママスターへリンクする形でテーブル（`schema.materials.json`）を作成し、`MATERIALS_TABLE_ID` に記録する。以後、レコードは**人がBase画面で直接追加する**（タイトル・画像・備考・テーマリンク・使用フラグ）。使用フラグONの素材だけが、対応テーマ（または「共通」）の画像生成時に参照候補になり、備考の文言がそのままプロンプトに反映される。

## 5. 素材投入の導線（Chrome拡張機能）

`extension/lark-quick-send/` を Chrome の「パッケージ化されていない拡張機能を読み込む」で導入。
オプション画面で、各テーマ（＋必要ならバックボーンストック）の取込元チャットに紐づく **Lark カスタムボットの Webhook URL** を登録する
（Webhook は各チャットの「ボット → カスタムボットを追加」で発行。4-1で既に発行済みならその値を使う）。
以後、Webページの選択テキストやリンクを右クリック →「Lark クイック送信」でテーマ別チャットへ送れる。

## 6. 実行

- 手動: `/sns-run`（取込→投稿作成をその場で実行）。
- 自動: `engine/run_pipeline.sh` を launchd / cron で1日1回程度。`SNS_PIPELINE_HOME` と `AGENT_CMD`
  （`claude -p` または `codex exec`）を環境変数で渡す。

生成物は Base の下書き。SNS への自動投稿はしない（人が確認して投稿する）。

## トラブルシューティング

- `SKIP: config incomplete` → `BASE_TOKEN` / `TABLE_ID_SOURCES` / 有効な `THEMES` のいずれかが未設定。
- 取込が Lark API エラー → Bot のスコープ（`im:message:readonly` / Bitable 書込）を確認。
- 画像が生成されない → `codex exec` が使えるか、画像生成モデルが有効かを確認。0枚でも本文は登録される。
- `ingest_backbone_stock.py` が exit 2 を返す → 正常（`BACKBONE_STOCK.ENABLED` が未設定/false、または未使用の任意機能）。パイプライン全体は止まらない。
- チャット読取が0件・権限エラー → 読取用アカウント（`CHAT_PROFILE`/`CHAT_IDENTITY=user`）がそのチャットのメンバーに入っているか確認（4-1参照）。
