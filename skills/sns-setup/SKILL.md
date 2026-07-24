---
name: sns-setup
description: SNS投稿パイプラインを新しいテナント（他社）で使えるように初期セットアップする。Lark Baseのテーブル作成（素材案・テーマ別投稿管理）、config雛形の配置、Larkクイック送信 Chrome拡張機能の導入案内、定期実行の設定までを案内する。
---

# sns-setup — 初期セットアップ

新しいテナントでこのパイプラインを立ち上げる。

## 手順
1. `"${CLAUDE_PLUGIN_ROOT}/engine/setup_prompt.md"` を読み、その手順に従う。
2. 前提確認（テナント自身の Lark Custom App / lark-cli プロファイル / 対象Baseとbot招待）→ ランタイム用意（config雛形コピー）→ 参考元テーブル作成 → テーマ作成（`sns-theme` の追加を必要数）→ 素材投入導線（拡張機能）→ 定期実行 → 動作確認。
3. 拡張機能は `"${CLAUDE_PLUGIN_ROOT}/extension/lark-quick-send/"` をChromeに読み込み、各テーマの Webhook URL をオプション画面で登録する。

## 注意
- **開発者（配布元）の資格情報は使わない。** 各テナントが自分の Lark App・Webhook・Base を使う。
- Bot自身では Base を作らない（ユーザーがBaseを作りbotを招待する運用を推奨）。
- 既存のテーブル・データがある場合、不足フィールドの追加のみ行い、改名・削除はしない。
