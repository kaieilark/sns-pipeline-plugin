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

## 構成

```
.claude-plugin/     Claude Code プラグイン定義（marketplace.json / plugin.json）
AGENTS.md           Codex 用のエントリ（両エージェント向けの全体説明）
skills/             Claude Code スキル（sns-run / sns-settings / sns-theme / sns-setup）
codex/prompts/      Codex プロンプト（同名）
engine/             ロジックの正本（ingest.py / compose_prompt.md / theme・settings・setup 指示書 / run_pipeline.sh）
templates/          設定・テーブルスキーマ・バックボーン/画像テイストの雛形＋架空デモテーマ
extension/          Lark クイック送信 Chrome拡張機能（Webhookはブラウザ保存・配布物にデータなし）
docs/               セットアップ手順
install.sh          スキル/プロンプトの導入とランタイム雛形の作成
```

## 導入（クイックスタート）

```bash
git clone <this private repo> ~/sns-pipeline-plugin
cd ~/sns-pipeline-plugin
./install.sh
```

その後:
1. `~/.sns-pipeline/config.json` に、自社の `PROFILE`（lark-cli プロファイル）・`BASE_TOKEN` 等を設定
2. `/sns-setup` … Base テーブル作成・拡張機能導入・動作確認
3. `/sns-settings` … テーマ追加・バックボーン・画像テイストの設定
4. `/sns-run` … 取込→投稿作成

詳細は [`docs/SETUP.md`](docs/SETUP.md)。

## 重要: 会員データについて

このリポジトリは**配布用テンプレートとエンジンのみ**。BASE_TOKEN・チャットID・Webhook・実際の
バックボーン内容・ロゴなどの**テナント固有データは一切含まない**。実データは各テナントの
`SNS_PIPELINE_HOME`（既定 `~/.sns-pipeline`）にのみ置かれ、リポジトリには入らない（`.gitignore` で二重防御）。

## Claude Code / Codex 両対応

- Claude Code: `skills/` のスキル（マーケットプレイス導入 or `install.sh`）。
- Codex: `codex/prompts/` を `~/.codex/prompts/` へ（`install.sh` が実施）＋ `AGENTS.md` を参照。
- どちらもロジックは `engine/` を共有するため、挙動は同じ。
