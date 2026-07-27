# インストール方法（詳細）

前提: Node.js 16+ / Python 3 / lark-cli / Claude Code もしくは Codex。

## 1. npm（GitHubから）— 認証不要・最短

公開リポジトリなので、GitHubアカウントなしでそのまま入る。

```bash
npm install -g github:kaieilark/sns-pipeline-plugin
sns-pipeline install
```

- `install` が Claude Code スキル（`~/.claude/skills/`）と Codex プロンプト（`~/.codex/prompts/`）を導入し、
  ランタイム `~/.sns-pipeline/`（`SNS_PIPELINE_HOME` で変更可）に `config.json` 雛形を作る。
- 特定バージョンを固定したい場合: `npm i -g github:kaieilark/sns-pipeline-plugin#v1.4.0`（タグ運用時）。

## 2. npm 公開レジストリ（無効・ライセンス上）

**このパッケージは再配布を厳格に禁止しているため、公開npmレジストリ（npmjs.com）への publish は行わない。**
`package.json` に `"private": true` を設定してあり、`npm publish` は実行できない（誤公開防止）。
配布は下記の「1. GitHubから」または「4. tarball」の、著作者が管理する経路のみとする。

## 3. git clone

```bash
git clone https://github.com/kaieilark/sns-pipeline-plugin.git ~/sns-pipeline-plugin
cd ~/sns-pipeline-plugin && ./install.sh
```

## 4. tarball（オフライン／レジストリ非依存）

配布元で作成:

```bash
npm pack        # kaieilark-sns-pipeline-<version>.tgz を生成
```

受け取った側:

```bash
npm install -g ./kaieilark-sns-pipeline-1.4.0.tgz
sns-pipeline install
```

## 5. Claude Code プラグイン（マーケットプレイス）

Claude Code のプラグイン機構で入れる場合、marketplace として本リポジトリを追加する:

```
/plugin marketplace add kaieilark/sns-pipeline-plugin
/plugin install sns-pipeline@sns-pipeline
```

（`.claude-plugin/marketplace.json` / `plugin.json` を同梱済み。`${CLAUDE_PLUGIN_ROOT}` はプラグイン機構が解決する）

## アンインストール

```bash
npm uninstall -g @kaieilark/sns-pipeline   # または github/tarball 版
# 手動導入したスキル/プロンプトを消す場合:
rm -rf ~/.claude/skills/sns-{run,settings,theme,setup}
rm -f  ~/.codex/prompts/sns-{run,settings,theme,setup}.md
# ランタイム(~/.sns-pipeline)は実データなので残す。不要なら手動削除。
```

## 前提の点検

```bash
sns-pipeline doctor
```

node / python3 / lark-cli / ~/.claude / ~/.codex / ランタイムの有無を表示する。
