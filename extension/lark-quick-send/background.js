// Lark クイック送信 - background service worker (Manifest V3)
// 選択テキスト／リンクを右クリックメニューから、登録済みの任意のLarkチャットへ送信する。

// importScripts は同期実行されるため、この直後のリスナー登録が
// service worker の初期評価中に確実に完了する。
// （ES モジュール化すると休止からの起床時にイベントを取りこぼす。詳細は shared.js 冒頭）
importScripts("shared.js");

const { loadChats, postToWebhook } = LarkShared;

const ROOT_ID = "lark-quick-send";
const CHILD_PREFIX = "lark-quick-send:";
const CONTEXTS = ["selection", "link", "image"];

// 何も選択しておらず、リンクでも画像でもない場所を右クリックしたときだけ
// 表示される「ページ自体を送る」メニュー。'page' はより具体的なコンテキスト
// （selection/link/image等）に該当しない場合のフォールバックとしてのみ発火する。
const PAGE_ROOT_ID = "lark-quick-send-page";
const PAGE_CHILD_PREFIX = "lark-quick-send-page:";
const PAGE_CONTEXTS = ["page"];

// 直前の再構築が終わるまで次を待たせるための直列化キュー。
//
// rebuildMenus は await を含むため、拡張の起動直後や設定の連続変更で
// 複数回同時に走ると、A が読み込んだ古い一覧で作った後に B の removeAll が
// 走る（またはその逆）という競合が起きる。実際に「2件登録済みなのに
// サブメニューが出ず単独項目のまま」「同一IDのcreateが二重に走る」という
// 不具合が発生したため、必ず1つずつ順番に実行する。
let rebuildQueue = Promise.resolve();

function rebuildMenus() {
  rebuildQueue = rebuildQueue.then(doRebuildMenus).catch((err) => {
    console.error("メニューの再構築に失敗しました", err);
  });
  return rebuildQueue;
}

// 右クリックメニューを、現在の登録内容から組み立て直す。
// 送信先0件・1件・複数件で最適な形が異なるため、毎回removeAllしてから作る。
async function doRebuildMenus() {
  const chats = await loadChats();

  await new Promise((resolve) => chrome.contextMenus.removeAll(resolve));

  // 「チャットに送信する」（選択テキスト／リンク／画像）と
  // 「このページをチャットに送信する」（ページURL）は独立した2本のメニューツリー。
  // 後者を後から作ることで、常に前者の直下に表示される。
  await buildMenuTree(chats, {
    rootId: ROOT_ID,
    childPrefix: CHILD_PREFIX,
    title: "Larkチャットへ送信",
    setupTitle: "Larkチャットへ送信（送信先を登録）",
    contexts: CONTEXTS
  });

  await buildMenuTree(chats, {
    rootId: PAGE_ROOT_ID,
    childPrefix: PAGE_CHILD_PREFIX,
    title: "このページをチャットに送信する",
    setupTitle: "このページをチャットに送信する（送信先を登録）",
    contexts: PAGE_CONTEXTS
  });
}

// 送信先0件・1件・複数件で最適な形が異なる（単独項目 or 親子メニュー）ため、
// メニューツリーを1本組み立てる処理を共通化する。
async function buildMenuTree(chats, { rootId, childPrefix, title, setupTitle, contexts }) {
  if (chats.length === 0) {
    // 未登録時は押すと設定画面へ誘導する単独項目にする。
    await createMenu({ id: rootId, title: setupTitle, contexts });
    return;
  }

  if (chats.length === 1) {
    // 1件だけならサブメニューを挟まず、そのまま送れるようにする。
    await createMenu({ id: `${childPrefix}${chats[0].id}`, title, contexts });
    return;
  }

  // 複数件は親メニュー＋送信先名のサブメニューにする。
  await createMenu({ id: rootId, title, contexts });

  for (const chat of chats) {
    await createMenu({ id: `${childPrefix}${chat.id}`, parentId: rootId, title: chat.name, contexts });
  }
}

// contextMenus.create は失敗しても例外を投げず lastError に入るだけなので、
// 握りつぶさずに検知できるようPromise化して確認する。
function createMenu(props) {
  return new Promise((resolve, reject) => {
    chrome.contextMenus.create(props, () => {
      const err = chrome.runtime.lastError;
      if (err) {
        reject(new Error(`${props.id}: ${err.message}`));
        return;
      }
      resolve();
    });
  });
}

// 拡張の更新・ブラウザ起動時にメニューを作り直す。
chrome.runtime.onInstalled.addListener(() => {
  rebuildMenus();
});

chrome.runtime.onStartup.addListener(() => {
  rebuildMenus();
});

// 設定画面で送信先が変わったら、メニューへ即座に反映する。
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.chats) {
    rebuildMenus();
  }
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  const menuId = String(info.menuItemId);

  // 送信先未登録の状態でクリックされた場合は設定画面へ誘導する。
  if (menuId === ROOT_ID || menuId === PAGE_ROOT_ID) {
    notify("Lark クイック送信", "設定画面で送信先チャットを登録してください。");
    chrome.runtime.openOptionsPage();
    return;
  }

  const isPageMenu = menuId.startsWith(PAGE_CHILD_PREFIX);
  const isContentMenu = !isPageMenu && menuId.startsWith(CHILD_PREFIX);

  if (!isPageMenu && !isContentMenu) {
    return;
  }

  const chatId = isPageMenu ? menuId.slice(PAGE_CHILD_PREFIX.length) : menuId.slice(CHILD_PREFIX.length);
  const chats = await loadChats();
  const chat = chats.find((c) => c.id === chatId);

  if (!chat) {
    // 設定変更とクリックが競合してメニューが古い場合に備える。
    notify("Lark クイック送信", "送信先が見つかりませんでした。設定画面を確認してください。");
    rebuildMenus();
    return;
  }

  const text = isPageMenu ? extractPageUrl(info) : extractPayload(info);

  if (!text) {
    const message = isPageMenu
      ? "ページのURLを取得できませんでした。"
      : "テキスト・リンク・画像のいずれかを選択（または右クリック）してください。";
    notify("Lark クイック送信", message);
    return;
  }

  const result = await postToWebhook(chat.url, text);

  if (!result.ok) {
    notify(`Lark クイック送信 - 送信失敗（${chat.name}）`, `送信に失敗しました: ${result.reason}`);
    return;
  }

  notify(`Lark クイック送信 - 送信成功（${chat.name}）`, buildSuccessMessage(text));
});

// 右クリック情報から送信すべきテキストを抽出する。
//
// 優先順位: リンク > 画像 > 選択テキスト。
// リンク（ボタン風のリンク・テキストリンクを問わず）を右クリックした場合は、
// その内部で文字列を選択していたとしても常にリンク先URLを送る
// （2026-08-04 会長指示: リンクとなっている部分は選択の有無に関係なく
// 常にリンク全体を送信対象にする）。旧バージョンは選択テキストを優先していたが、
// この指示により意図的に優先順位を反転させている。
function extractPayload(info) {
  if (info.linkUrl) {
    return info.linkUrl;
  }

  if (info.mediaType === "image" && info.srcUrl) {
    return info.srcUrl;
  }

  const selection = (info.selectionText || "").trim();
  if (selection) {
    return selection;
  }

  return "";
}

// 「このページをチャットに送信する」用: 右クリックされたページ自体のURLを送る。
function extractPageUrl(info) {
  return (info.pageUrl || "").trim();
}

function buildSuccessMessage(text) {
  const preview = text.length > 60 ? `${text.slice(0, 60)}...` : text;
  return `送信しました: ${preview}`;
}

function notify(title, message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon128.png",
    title,
    message
  });
}
