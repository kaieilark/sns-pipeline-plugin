# 変更履歴

## 1.5.1

- **Chrome拡張機能の導入手順を、クリック単位の具体的な案内に拡張。** `chrome://extensions` を開く→デベロッパーモードON→「パッケージ化されていない拡張機能を読み込む」→フォルダ選択、までを省略なく明記（`engine/setup_prompt.md` §4-1新設、`docs/SETUP.md` §5-1）。拡張機能はファイルとしては一緒にダウンロードされるが、Chromeへの読み込みだけはブラウザの仕様上どうしても手動になる旨を明示（Claude Code/Codexどちらでも同じ制約）。
- **Codex CLI本体をまだ持っていない場合の導入手順を追加**（`engine/setup_prompt.md` §0-6-1新設、`docs/SETUP.md` §2-1）。`npm install -g @openai/codex` での導入、初回認証が必要な旨、導入が難しい場合は `openai_api` へ切り替える代替案を明記。
- `engine/setup_prompt.md` §0-1 用語集に「Codex」「拡張機能」の行を追加。
- `docs/SETUP.md` §1 のインストール例を、実態（公開npm配布）に合わせて `git clone <this private repo>` から `npm install -g github:...` に修正（既存の矛盾を解消）。

## 1.5.0

- **対話設計を大幅強化: 専門用語を知らない利用者向けの手厚いサポートに対応。** これまでの指示書は「何を聞くか」の技術的な手順書としては完成していたが、「テーマ」「バックボーン」等の専門用語を利用者が知っている前提で書かれており、`config.json` のキー名をそのまま尋ねる想定になっていた。
  - `engine/setup_prompt.md` に **§0-1「対話の進め方（初めてのユーザー向け・必読）」を新設**。対話の基本姿勢（1つずつ聞く・専門用語は言い換えてから使う・具体例を必ず添える・任意機能は無理に埋めさせない）と、主要用語（テーマ／バックボーン／画像テイスト／バックボーンストック／素材ライブラリ／画像生成の方法）の**平易な説明文と尋ね方の例をそのまま使える形で用語集化**。
  - `engine/theme_prompt.md` B（テーマ追加）・C（バックボーン設定）・D（画像テイスト設定）を、技術キーを直接尋ねる形から、**先に一言で説明してから日本語で1つずつ聞く対話形式**に全面改訂。
  - `engine/setup_prompt.md` §0-6（画像生成バックエンドの選択）の3択に、専門用語が分からない場合の平易な言い換え（例:「他にお使いのAIツールで画像を作らせる」）を追加。
  - `engine/settings_prompt.md` に、メニュー選択後は選ばれた項目を一言かみ砕いて説明してから作業する指示を追加。
  - 全 skill（Claude Code）・Codex プロンプト・`AGENTS.md` / `README.md` / `docs/SETUP.md` から §0-1 を参照するよう統一。

## 1.4.0

- **「テーマ」を正規化されたマスターテーブル構成に変更**（実運用での再設計を反映）。従来は参考元テーブルに「テーマ」を単一選択(select)として持たせ、テーマ追加のたびに選択肢を足していたが、複数テーブル（参考元・素材ライブラリ等）に同じ選択肢を重複させると同期漏れの温床になるため、テーママスターテーブル（`THEME_MASTER_TABLE_ID`。各テーマ＋「共通」が1レコード）を新設。参考元テーブルの「テーマ」は「テーマリンク」（link・書込対象）＋「テーマ」（formula: `FIRST([テーマリンク].[NAME])`・読取専用）の構成に変更。テーマの追加・改名はマスター側の1レコードを直すだけで全体に反映される。
  - `templates/schema.theme_master.json` を新設。`templates/schema.sources.json` の「テーマ」フィールドをlink+formula構成に更新。
  - `templates/config.example.json`: `THEME_MASTER_TABLE_ID` / `SHARED_THEME_RECORD_ID`（トップレベル）、`THEMES[].THEME_RECORD_ID` を追加。
  - `engine/ingest.py`: `load_themes()` が `THEME_RECORD_ID` を必須化。「テーマ」への書込を `[{"id": theme_record_id}]`（link CellValue）に変更。
  - `engine/setup_prompt.md` §2 をテーママスター作成込みの手順に全面改訂。`engine/theme_prompt.md` B（追加）にテーママスターへのレコード作成手順を追加（select選択肢の追加操作は廃止）。
- **素材ライブラリ（任意機能）を新設**。画像生成時に参照する既定素材（店舗オーナー写真・ロゴ等）をBaseで管理し、使用フラグ(checkbox)ONの素材だけを参照候補にする。備考欄の説明（例: 服装の変更は許可します）がそのまま画像生成プロンプトに反映される。テーマリンクで対象テーマ、または「共通」を指定できる。
  - `templates/schema.materials.json` を新設。`config.example.json` に `MATERIALS_TABLE_ID` を追加。
  - `engine/compose_prompt.md` §5-0 に、使用フラグONかつ対象テーマ（または共通）に一致する素材を取得し参照画像・プロンプトへ反映する手順を追加。`engine/setup_prompt.md` §3-3（新設）。
- 上記2点は `engine/settings_prompt.md`（メニュー項目追加）・各 skill / Codex プロンプト・`AGENTS.md` / `README.md` / `docs/SETUP.md` に反映。

## 1.3.0

- **バックボーンストックのテーブル設計を修正**（実運用での再設計を反映）。固定（プライマリ）フィールドを「タイトル」（内容依存のテキスト）から「ID」（auto_number・自動採番）に変更。「投稿者名」をLark標準のuser型フィールド化し、実在ユーザー（open_id）のときだけ `[{"id": open_id}]` を設定（bot/アプリ投稿は空のまま。名前・アイコンをLarkが自動解決し、SENDER_NAME_MAPのような手動マップが不要に）。書込形式を `{"fields":[...],"rows":[...]}` から `{"create_records":[...]}` に変更。`templates/schema.backbone_stock.json` と `engine/ingest_backbone_stock.py` を全面更新。
- **新規テーブル設計の原則をドキュメント化**（`AGENTS.md` / `engine/setup_prompt.md`）: 固定フィールドは内容依存にしない。既存データがあるテーブルへの応急処置と、未使用の新規テーブル（ゼロベースで正しい設計を選べる）は状況が違う、という教訓を明記。
- **画像生成バックエンドの選択機能を追加**（`IMAGE_BACKEND` / `IMAGE_BACKEND_CONFIG`）。実行中のエージェントが画像生成モデルを持つとは限らないため、セットアップ時に明示的に選ぶ:
  - Claude Code等（画像生成モデルを持たない）で導入した場合 → 必ずユーザーに3択を尋ねる: `codex_cli`（別途インストール済みcodex CLIのサブスクリプション・既定の推奨）／`openai_api`（従量課金のOpenAI Images API）／`custom_script`（自作スクリプト）。
  - Codex自身に導入した場合 → 確認なしで自動的に `codex_native`（Codex自身のimage_gen機能を直接使用。サブプロセス起動なし）。
  - `engine/compose_prompt.md` §5-1 を4バックエンド対応に全面改訂。`engine/setup_prompt.md` §0-6（新設）、`engine/settings_prompt.md`（メニュー項目11）、各skill/Codexプロンプトに反映。

## 1.2.0

- **バックボーンストック（継続蓄積・任意機能）を追加**。特定のチャットに随時書き溜められる思い・方針・エピソードを、テーマを問わず本文作成のレンズとして自動参照する機能（`BACKBONE_STOCK` / `engine/ingest_backbone_stock.py` / `templates/schema.backbone_stock.json`）。テーマ別の `BACKBONE_FILE`（静的・随時編集）とは別物。
- **チャットが存在しない場合の作成ガイドを追加**（`engine/setup_prompt.md` §0-5）。テーマ追加・バックボーンストック設定でチャットIDが未確定な場合、対話でLarkグループチャット作成〜カスタムボットのWebhook発行までを案内し、得られた値をその場で `config.json` に登録する。テーマ管理・統括設定の各指示書から共通で参照する。
- **画像枚数のルールを改訂**: 「既定1枚」から「1〜5枚を内容の情報量に応じて決定」に変更。固定既定（1枚にも特定枚数にも）へ寄らないよう明記。見出し文字サイズを画像高さ10%程度に統一。ミニマルな骨格を選ぶ場合もテーマの背景モチーフを十分な面積で残す制約を追加。§5-0 に情報密度目安を明文化（以前は欠落していた）。
- **公開済み投稿との整合性チェックを追加**（`compose_prompt.md` 4-4）。同一テーマの公開済み投稿と矛盾する主張・トーンにならないか、本文作成の最後に確認する。
- **`ingest.py` の送信者フィルタを撤廃**。`sender_type=="user"` 限定をやめ、bot連携で投稿された内容も参考元候補として取り込む。あわせて「1メッセージ=1参考元」の絶対ルールを明記（隣接メッセージの誤統合防止）。
- `engine/compose_prompt.md` 手順1に、バックボーンストックの実際の読み取りコマンドを追加（絶対ルールはあったが実行手順が無かった不整合を解消）。

## 1.1.0

- npm配布対応（`bin/cli.js`）。GitHubからの `npm install` / tarball配布に対応。
- ライセンスをプロプライエタリ（再配布厳格禁止）に変更、`package.json` を `private: true` に設定。

## 1.0.0

- 初版。テーマ複数対応・テーマ別投稿テーブル分割・バックボーン/画像テイストの後編集・画像骨格の直近10件非重複・Claude Code/Codex両対応・Lark クイック送信 Chrome拡張機能同梱。
