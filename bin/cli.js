#!/usr/bin/env node
/*
 * sns-pipeline CLI — 依存ゼロ（Node標準のみ）。
 * npm 経由で入れたパッケージから、Claude Code スキル / Codex プロンプト / ランタイム雛形を導入する。
 * 実データ（config・テーマ・状態）は SNS_PIPELINE_HOME(既定 ~/.sns-pipeline) に置き、パッケージには入れない。
 *
 * 使い方:
 *   npx @kaieilark/sns-pipeline install   スキル/プロンプト/ランタイム雛形を導入
 *   npx @kaieilark/sns-pipeline doctor     前提(node/python3/lark-cli)を点検
 *   npx @kaieilark/sns-pipeline path        パッケージの配置先を表示
 *   npx @kaieilark/sns-pipeline help
 */
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

const PKG_ROOT = path.resolve(__dirname, '..');
const HOME = os.homedir();
const RUNTIME = process.env.SNS_PIPELINE_HOME || path.join(HOME, '.sns-pipeline');
const SKILLS = ['sns-run', 'sns-settings', 'sns-theme', 'sns-setup'];

function log(s) { process.stdout.write(s + '\n'); }
function exists(p) { try { fs.accessSync(p); return true; } catch { return false; } }
function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }

function copyDir(src, dst) {
  mkdirp(dst);
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

function which(cmd) {
  try {
    const out = execSync(process.platform === 'win32' ? `where ${cmd}` : `command -v ${cmd}`, { stdio: ['ignore', 'pipe', 'ignore'] });
    return out.toString().trim().split('\n')[0] || null;
  } catch { return null; }
}

function installClaudeSkills() {
  const base = path.join(HOME, '.claude');
  if (!exists(base)) { log('[skip] ~/.claude が無いため Claude Code スキルはスキップ'); return; }
  const dest = path.join(base, 'skills');
  for (const s of SKILLS) {
    const srcFile = path.join(PKG_ROOT, 'skills', s, 'SKILL.md');
    if (!exists(srcFile)) continue;
    const dDir = path.join(dest, s);
    mkdirp(dDir);
    let body = fs.readFileSync(srcFile, 'utf8').split('${CLAUDE_PLUGIN_ROOT}').join(PKG_ROOT);
    fs.writeFileSync(path.join(dDir, 'SKILL.md'), body);
  }
  log(`[OK] Claude Code スキルを ${dest} に導入`);
}

function installCodexPrompts() {
  const base = path.join(HOME, '.codex');
  if (!exists(base)) { log('[skip] ~/.codex が無いため Codex プロンプトはスキップ'); return; }
  const dest = path.join(base, 'prompts');
  mkdirp(dest);
  for (const s of SKILLS) {
    const srcFile = path.join(PKG_ROOT, 'codex', 'prompts', s + '.md');
    if (!exists(srcFile)) continue;
    const body = fs.readFileSync(srcFile, 'utf8').split('$SNS_PLUGIN_ROOT').join(PKG_ROOT);
    fs.writeFileSync(path.join(dest, s + '.md'), body);
  }
  log(`[OK] Codex プロンプトを ${dest} に導入（SNS_PLUGIN_ROOT=${PKG_ROOT}）`);
}

function scaffoldRuntime() {
  for (const d of ['themes', 'logs', 'images', 'tmp']) mkdirp(path.join(RUNTIME, d));
  const cfg = path.join(RUNTIME, 'config.json');
  if (!exists(cfg)) {
    fs.copyFileSync(path.join(PKG_ROOT, 'templates', 'config.example.json'), cfg);
    log(`[OK] ${cfg} を雛形から作成（BASE_TOKEN 等を埋めてください）`);
  } else {
    log(`[keep] ${cfg} は既存のため保持`);
  }
}

function cmdInstall() {
  log('== @kaieilark/sns-pipeline install ==');
  log(`package : ${PKG_ROOT}`);
  log(`runtime : ${RUNTIME}`);
  installClaudeSkills();
  installCodexPrompts();
  scaffoldRuntime();
  log('');
  log('== 次のステップ ==');
  log(`1. ${path.join(RUNTIME, 'config.json')} に自社の PROFILE / BASE_TOKEN 等を設定`);
  log('2. 初期セットアップ: Claude Code -> /sns-setup  /  Codex -> /sns-setup');
  log('3. テーマ設定:       /sns-settings（テーマ追加・バックボーン・画像テイスト）');
  log('4. 実行:             /sns-run');
  log(`拡張機能: ${path.join(PKG_ROOT, 'extension', 'lark-quick-send')} を Chrome に読み込み、各テーマの Webhook を登録`);
}

function cmdDoctor() {
  log('== doctor ==');
  log(`node        : ${process.version}`);
  const py = which('python3') || which('python');
  log(`python3     : ${py || '見つかりません（ingest.py 実行に必要）'}`);
  const lark = which('lark-cli');
  log(`lark-cli    : ${lark || '見つかりません（Lark操作に必要）'}`);
  log(`~/.claude   : ${exists(path.join(HOME, '.claude')) ? 'あり（Claude Code）' : 'なし'}`);
  log(`~/.codex    : ${exists(path.join(HOME, '.codex')) ? 'あり（Codex）' : 'なし'}`);
  log(`runtime home: ${RUNTIME} ${exists(RUNTIME) ? '(あり)' : '(未作成)'}`);
  log(`config.json : ${exists(path.join(RUNTIME, 'config.json')) ? 'あり' : 'なし（install で作成）'}`);
}

function cmdHint() {
  // postinstall から呼ばれる。副作用なし（ファイルを書かない）。
  log('');
  log('[@kaieilark/sns-pipeline] インストール完了。次を実行して有効化してください:');
  log('  npx @kaieilark/sns-pipeline install   # スキル/プロンプト/雛形を導入');
  log('  npx @kaieilark/sns-pipeline doctor     # 前提を点検');
  log('');
}

function cmdHelp() {
  log('sns-pipeline — テーマ別SNS投稿パイプライン（Claude Code / Codex 両対応）');
  log('');
  log('使い方:');
  log('  npx @kaieilark/sns-pipeline <command>');
  log('');
  log('コマンド:');
  log('  install   Claude Code スキル / Codex プロンプト / ランタイム雛形を導入');
  log('  doctor    前提（node / python3 / lark-cli / ~/.claude / ~/.codex）を点検');
  log('  path      パッケージの配置先を表示');
  log('  help      このヘルプ');
  log('');
  log('導入後は、エージェント側で /sns-setup → /sns-settings → /sns-run。');
}

const cmd = (process.argv[2] || 'help').toLowerCase();
try {
  if (cmd === 'install') cmdInstall();
  else if (cmd === 'doctor') cmdDoctor();
  else if (cmd === 'path') log(PKG_ROOT);
  else if (cmd === 'hint') cmdHint();
  else cmdHelp();
} catch (e) {
  process.stderr.write('エラー: ' + (e && e.message ? e.message : String(e)) + '\n');
  process.exit(1);
}
