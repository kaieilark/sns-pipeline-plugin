# SNS投稿パイプライン プラグイン

Larkチャットに集めた素材（記事URL・コメント）から、**テーマ別に**SNS投稿の下書き
（Instagram / Threads / X の本文＋参考画像）を作り、Lark Base へ蓄積する配布用パイプライン。
**Claude Code と Codex の両方**で使える。

## 何ができるか

- **テーマを複数運用**できる（例:「会社ブランディング用」「募集用」）。テーマは設定に足すだけで増やせる。
- **投稿（記事）はテーマごとに別テーブル**に分けて管理。素材案はチャットIDで振り分くので全テーマ共通の1テーブルでよい。
- **バックボーン（背景・思想）**をテーマごとに設定。HPのURL / 直接入力 / 資料ファイル から作れ、後からいつでも変更可能。
- **画像テイスト**をテーマごとに設定。Instagram等のURL / 画像添付 / 説明文 で指定でき、後から変更可能。
- **画像の骨格を直近10枚で重複させない**（毎回レイアウトの型を変える）。テーマ別にローテーション管理。
- 記事は「読み手の教育 → 問い合わせへの誘導」方針。画像は画像生成モデルのみで文字・ロゴまで描く。
- 素材投入用の **Chrome拡張機能**（Lark クイック送信）同梱。右クリックでテーマ別チャットへ投げ込める。

## インストール

前提: Node.js 16+ / Python 3 / [lark-cli](https://github.com/) / Claude Code もしくは Codex。

### 方法A: npm（GitHubから・最短）

公開リポジトリなので、認証なしでそのまま入る。

```bash
npm install -g github:kaieilark/sns-pipeline-plugin
sns-pipeline install     # スキル/プロンプト/ランタイム雛形を導入
sns-pipeline doctor      # 前提を点検
```

`npx` で単発実行もできる:

```bash
npx github:kaieilark/sns-pipeline-plugin install
```

### 方法B: git clone

```bash
git clone https://github.com/kaieilark/sns-pipeline-plugin.git ~/sns-pipeline-plugin
cd ~/sns-pipeline-plugin && ./install.sh
```

### 方法C: tarball（オフライン配布）

`npm pack` で作った `.tgz`、または配布された tar を渡された場合:

```bash
npm install -g ./kaieilark-sns-pipeline-1.1.0.tgz
sns-pipeline install
```

インストール方法の詳細と、公開npmへの publish 手順は [`docs/INSTALL.md`](docs/INSTALL.md)。

## 使い方（導入後）

エージェント側で:

1. `~/.sns-pipeline/config.json` に、自社の `PROFILE`（lark-cli プロファイル）・`BASE_TOKEN` 等を設定
2. `/sns-setup` … Base テーブル作成・拡張機能導入・動作確認
3. `/sns-settings` … テーマ追加・バックボーン・画像テイストの設定
4. `/sns-run` … 取込→投稿作成

- **Claude Code**: `skills/` のスキルを使う（`sns-run` / `sns-settings` / `sns-theme` / `sns-setup`）。
- **Codex**: `~/.codex/prompts/` の同名プロンプトを `/sns-run` 等で呼ぶ（`AGENTS.md` も参照）。

詳細は [`docs/SETUP.md`](docs/SETUP.md)。

## CLI

```
sns-pipeline install   スキル / Codexプロンプト / ランタイム雛形を導入
sns-pipeline doctor    前提（node / python3 / lark-cli / ~/.claude / ~/.codex）を点検
sns-pipeline path      パッケージの配置先を表示
sns-pipeline help
```

## 構成

```
package.json        npm パッケージ定義（bin: sns-pipeline）
bin/cli.js          インストーラ CLI（依存ゼロ）
.claude-plugin/     Claude Code プラグイン定義（marketplace.json / plugin.json）
AGENTS.md           Codex 用エントリ（両エージェント向けの全体説明）
skills/             Claude Code スキル（sns-run / sns-settings / sns-theme / sns-setup）
codex/prompts/      Codex プロンプト（同名）
engine/             ロジックの正本（ingest.py / compose_prompt.md / theme・settings・setup 指示書 / run_pipeline.sh）
templates/          設定・テーブルスキーマ・バックボーン/画像テイストの雛形＋架空デモテーマ
extension/          Lark クイック送信 Chrome拡張機能（Webhookはブラウザ保存・配布物にデータなし）
docs/               INSTALL / SETUP 手順
```

## 重要: データについて

このリポジトリは**配布用テンプレートとエンジンのみ**で、公開しても安全なように作られている。
BASE_TOKEN・チャットID・Webhook・実際のバックボーン内容・ロゴなどの**テナント固有データは一切含まない**。
実データは各テナントの `SNS_PIPELINE_HOME`（既定 `~/.sns-pipeline`）にのみ置かれ、リポジトリには入らない
（`.gitignore` で二重防御）。

## ライセンス

**プロプライエタリ（All Rights Reserved・ソース閲覧可）。再配布は厳格に禁止。**

ソースは公開・閲覧可能だが、権利はすべて留保する。**再配布（コピー・再アップロード・ミラー・別レジストリやマーケットプレイスへの掲載・第三者への配布/転載/貸与・フォークしての配布・他製品への同梱・再販・サブライセンス・サービスとしての提供）は、いかなる形態でも書面による許諾なしに固く禁止する。** 許諾された利用者が自社の1インスタンスを運用するための利用のみ認める。詳細は [`LICENSE`](LICENSE)。
