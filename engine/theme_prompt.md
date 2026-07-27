# テーマ管理 指示書（theme step・エージェント共通）

テーマ（会社ブランディング用・募集用…のような投稿系統）を追加・編集・一覧・停止・再開する。
ランタイムは `SNS_PIPELINE_HOME`（未設定なら `~/.sns-pipeline`）配下（以降 `$HOME_DIR`）。
配布物（プラグイン）側のテンプレートは、このファイルと同じ階層の `../templates/` にある（以降 `$TPL`）。

> **原則**: テーマを増やしても、既存テーマ・既存データには一切触れない。テーブル・レコードの削除はしない。
> 「テーマを削除」は物理削除ではなく `ENABLED:false`（停止）で行う。素材案テーブルは全テーマ共通の1つ、
> 投稿管理テーブルはテーマごとに分ける（作成する記事を分離する設計要件）。

## 事前確認
- `lark-cli base --help` で、テーブル作成・フィールド更新の正確なサブコマンド名を確認してから実行する
  （版により `+table-create` / `+field-update` 等の綴りが変わることがある）。
- 破壊的操作の前に `--dry-run` があれば使って想定ペイロードを確認する。

---

## A. 一覧表示（list）
`cat $HOME_DIR/config.json` を読み、`THEMES` を表で示す:
`THEME_KEY / NAME / THEME_RECORD_ID / ENABLED / CHAT_ID / TABLE_ID_POSTS / READER / GOAL / CTA_URL / BACKBONE_FILE / IMAGE_TASTE_FILE / LOGO_FILE`。
各テーマの `BACKBONE_FILE` が空か雛形のままなら「バックボーン未設定」、`IMAGE_TASTE_FILE` が雛形のままなら「画像テイスト未設定」、`THEME_RECORD_ID` が空なら「テーママスター未登録（要修復）」と付記する。

---

## B. 追加（add）
ユーザーから最低限これを聞く（不明なら安全な既定を置き、後で編集可能と伝える）:
- `THEME_KEY`（英小文字・ハイフンのみ。既存と重複不可）
- `NAME`（表示名。例「会社ブランディング」「講座募集」）
- `CHAT_ID`（このテーマの素材を集める取込元チャット。別チャットにすることでテーマが振り分けられる）
- `READER`（読者） / `GOAL`（最終ゴール） / `CTA_URL`（誘導先URL）
- `CHAT_NAME`（任意・表示用） / `WEBHOOK_URL`（任意・拡張機能の送信先。このタイミングで発行しておくと後で二度手間にならない）

**`CHAT_ID` を聞いた際、ユーザーが「まだ無い」「これから作る」と答えた場合、silentに進めず、必ず `setup_prompt.md` §0-5（チャットが存在しない場合の作成ガイド）を実行する。** ユーザーへ質問（既存チャットの有無）→ 無ければ作成手順を案内 → カスタムボットのWebhook発行を案内 → CHAT_ID解決 → **その場でconfig.jsonへ登録**、まで一連で行い、聞いた値を登録せずに次の手順へ進まない。

手順:
1. **テーママスターにレコードを作成する**（`THEME_MASTER_TABLE_ID` が未設定なら、先に `setup_prompt.md` §2 でテーママスター自体を作る）:
   `lark-cli --profile <cfg.PROFILE> base +record-create --base-token <BASE_TOKEN> --table-id <THEME_MASTER_TABLE_ID> --json '{"fields":{"NAME":"<NAME>","THEME_KEY":"<THEME_KEY>","DESCRIPTION":"<READERとGOALから作った短い説明>","CHAT_NAME":"<CHAT_NAME>"}}' --as bot`
   返った `record_id` を控える（これが `THEME_RECORD_ID`）。**参考元テーブルへ書き込む「テーマリンク」はこのrecord_idを使う。単一選択(select)の選択肢を追加する操作はもう行わない**（2026-07-27以降、系統/テーマはマスターテーブルへの正規化構成のため、参考元テーブル自体にオプション追加は不要）。
2. **投稿管理テーブルを作成**（テーマ専用）:
   - `$TPL/schema.posts.json` を読み、`name` の `__THEME_NAME__` を `NAME` に、`link_table` の `__SOURCES_TABLE_ID__` を config の `TABLE_ID_SOURCES` に置換する。
   - `lark-cli --profile <cfg.PROFILE> base +table-create --base-token <BASE_TOKEN> --json '<置換後のJSON>' --as bot` で作成し、返った `table_id` を控える。
3. **テーマ用フォルダを scaffold**:
   - `mkdir -p $HOME_DIR/themes/<THEME_KEY>/image_refs`
   - `$TPL/backbone.template.md` を `$HOME_DIR/themes/<THEME_KEY>/backbone.md` にコピーし `__THEME_NAME__` を置換
   - `$TPL/image_taste.template.md` を `$HOME_DIR/themes/<THEME_KEY>/image_taste.md` にコピーし `__THEME_NAME__` を置換
   - `engine/design_framework_log.template.json` を `$HOME_DIR/themes/<THEME_KEY>/design_framework_log.json` にコピー
4. **config.json に THEMES 要素を追記**（`THEME_RECORD_ID` は手順1、`TABLE_ID_POSTS` は手順2で得た値。`BACKBONE_FILE`=`themes/<KEY>/backbone.md`、`IMAGE_TASTE_FILE`=`themes/<KEY>/image_taste.md`、`LOGO_FILE`=空）。既存要素は変更しない。
5. **バックボーンと画像テイストの初期設定を促す**: 「続けてバックボーン（HP URL か直接入力）と画像テイスト（Instagram URL / 画像添付 / 説明）を設定しますか？」と尋ね、YesならC・Dへ進む。
6. 結果を報告する（作成した THEME_RECORD_ID・TABLE_ID_POSTS、scaffold したファイルパス）。

---

## C. バックボーン設定・修正（backbone）
対象テーマの `BACKBONE_FILE`（`$HOME_DIR/themes/<KEY>/backbone.md`）を作る/直す。入力方法は3通り:
1. **HP・LP等のURL** … 各ページ本文を取得（Lark文書URLは `lark-cli docs +fetch`、一般Webは取得手段で本文を得る）→ backbone.template の各節（何をしている/価値観/立ち位置/語り口/実例/禁止事項/正式表記）に要約して埋める。
2. **ユーザーが直接入力** … 聞き取った内容を各節に整理して書く。
3. **ローカル資料（MD/テキスト/議事録）** … 読み込んで各節に要約して埋める。
書き終えたら要点を提示し、実態と合っているかユーザーに確認する。**いつでも再実行して上書きできる**旨を伝える。

---

## D. 画像テイスト設定・変更（image taste）
対象テーマの `IMAGE_TASTE_FILE`（`$HOME_DIR/themes/<KEY>/image_taste.md`）を作る/直す。入力方法は3通り:
1. **Instagram等のURL** … `MODE: instagram_url` と `REFERENCE:` にURLを書く。**さらに、その世界観を PALETTE / MOOD / MOTIFS / PEOPLE / TYPOGRAPHY / FORBID に文章化して埋める**（自動ランがブラウザ操作に依存しないようにするため。可能ならURLを見て、無理なら聞き取りで埋める）。
2. **画像を添付** … 画像を `$HOME_DIR/themes/<KEY>/image_refs/` に保存し、`MODE: image` と `REFERENCE:` にそのパスを書く。PALETTE 等も可能な範囲で埋める。
3. **文章で説明** … `MODE: description` で PALETTE 等を直接書く。
- ロゴを画像に必ず入れる場合、ロゴ画像を `image_refs/` に置き、config の該当テーマ `LOGO_FILE` にそのパスを設定する。
- 「過去10枚で同じ骨格を繰り返さない」ローテーションは `design_framework_log.json`（テーマ別）で自動管理される。テイストを変えても履歴は引き継ぐ。

---

## E. 編集（edit）/ 停止・再開（enable）/ 削除（remove）
- edit: 指定テーマの `READER` `GOAL` `CTA_URL` `CTA_STYLE` `CHAT_ID` `CHAT_NAME` `WEBHOOK_URL` `NAME` を config で書き換える（バックボーン・画像テイストはC・Dで）。**`NAME` を変える場合は、テーママスター（`THEME_RECORD_ID` が指すレコード）の `NAME` フィールドも同じ値に更新する（`+record-update` 等）。ここがマスターであり、参考元テーブルの「テーマ」表示はこの値をformulaで参照しているため、config側だけ変えると表示がズレる。**
- enable/disable: `ENABLED` を true/false にする。false のテーマは取込・投稿作成の対象外になるが、テーブル・データ・watermark は保持され、再開できる（テーママスターのレコードもそのまま残す）。
- remove: **物理削除はしない。** `ENABLED:false` にし、必要なら NAME 末尾に「（停止）」等の注記を付ける（テーママスター側も同様に注記してよい）。テーブル削除が本当に必要な場合は、影響（発行済みリンク・既存レコード・他テーブルからのリンク）を説明し、ユーザーが Lark 画面で手動削除する運用にする。
