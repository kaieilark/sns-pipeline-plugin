---
name: sns-setup
description: SNS投稿パイプラインを新しいテナント（他社）で使えるように初期セットアップする。Lark Baseのテーブル作成（素材案・テーマ別投稿管理・バックボーンストック）、必要なチャットが無ければ作成〜Webhook発行まで対話で案内、config雛形の配置、Larkクイック送信 Chrome拡張機能の導入案内、定期実行の設定までを行う。
---

# sns-setup — 初期セットアップ

新しいテナントでこのパイプラインを立ち上げる。

## 手順
1. `"${CLAUDE_PLUGIN_ROOT}/engine/setup_prompt.md"` を読み、その手順に従う。
2. 前提確認（テナント自身の Lark Custom App / lark-cli プロファイル / 対象Baseとbot招待）→ ランタイム用意（config雛形コピー）→ **画像生成バックエンドの選択（§0-6・必須・下記参照）** → 参考元テーブル作成 → テーマ作成（`sns-theme` の追加を必要数）→ バックボーンストック（任意・§3-2）→ 素材投入導線（拡張機能）→ 定期実行 → 動作確認。
3. **取込元チャットが必要になったタイミング（テーマ追加・バックボーンストック設定）で、まだチャットが無い場合は engine/setup_prompt.md §0-5 に従い、対話でチャット作成〜カスタムボットのWebhook発行を案内し、得られた値をその場で config.json に登録する。** 聞きっぱなしで登録を忘れない。
4. 拡張機能は `"${CLAUDE_PLUGIN_ROOT}/extension/lark-quick-send/"` をChromeに読み込み、各テーマ（＋必要ならバックボーンストック）の Webhook URL をオプション画面で登録する。

## 画像生成バックエンドの選択（Claude Code実行時は必須・省略禁止）

**Claude Code自身は画像生成モデルを持たない。** `engine/setup_prompt.md` §0-6 に従い、**必ずユーザーに次の3択を尋ねる**（黙って既定値を設定しない）:
1. 「Codex CLIのサブスクリプションを使う」（`IMAGE_BACKEND=codex_cli`。別途 `codex` コマンドが必要。推奨として提示してよい）
2. 「OpenAI API等の従量課金APIを使う」（`IMAGE_BACKEND=openai_api`。APIキーの環境変数名を確認）
3. 「その他のAPI/ツールを自分で用意する」（`IMAGE_BACKEND=custom_script`。スクリプトパスを確認）

選ばれた値と関連設定（APIキー環境変数名・スクリプトパス）を、その場で `config.json` の `IMAGE_BACKEND` / `IMAGE_BACKEND_CONFIG` に登録する。

## 注意
- **開発者（配布元）の資格情報は使わない。** 各テナントが自分の Lark App・Webhook・Base を使う。
- Bot自身では Base を作らない（ユーザーがBaseを作りbotを招待する運用を推奨）。
- 既存のテーブル・データがある場合、不足フィールドの追加のみ行い、改名・削除はしない。
- バックボーンストックは任意機能。導入しなくてもテーマ別バックボーン（`BACKBONE_FILE`）と素材の要約だけで本文作成は成立する。
