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

## 3. テーブルを作る

`/sns-setup`（Codexも同名）を実行すると、指示書 `engine/setup_prompt.md` に沿って:
- **参考元テーブル（全テーマ共通）** を作成 → `TABLE_ID_SOURCES` に記録
- テーマごとに **投稿管理テーブル** を作成（`/sns-theme` の追加で）→ 各 `TABLE_ID_POSTS` に記録

> テーブル分割の考え方: **作成する記事（投稿）はテーマごとに別テーブル**。素材案はチャットIDで
> 振り分けられるので**全テーマ共通の1テーブル**でよい（「テーマ」フィールドで区別）。

## 4. テーマを設定する

`/sns-settings` → 「テーマを追加する」。各テーマで:
- `NAME`（表示名）/ `CHAT_ID`（素材を集めるチャット）/ `READER`（読者）/ `GOAL`（ゴール）/ `CTA_URL`（誘導先）
- **バックボーン**（背景・思想）: HPのURL / 直接入力 / 資料ファイル から作る（`themes/<key>/backbone.md`）。後から変更可。
- **画像テイスト**: Instagram URL / 画像添付 / 説明文（`themes/<key>/image_taste.md`）。後から変更可。
- **ロゴ**（任意）: 画像に必ず入れるロゴを登録（`LOGO_FILE`）。

## 5. 素材投入の導線（Chrome拡張機能）

`extension/lark-quick-send/` を Chrome の「パッケージ化されていない拡張機能を読み込む」で導入。
オプション画面で、各テーマの取込元チャットに紐づく **Lark カスタムボットの Webhook URL** を登録する
（Webhook は各チャットの「ボット → カスタムボットを追加」で発行）。
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
