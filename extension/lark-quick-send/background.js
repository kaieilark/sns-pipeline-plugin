// Lark クイック送信 - background service worker (Manifest V3)
// 選択テキスト／リンクを右クリックメニューからLarkカスタムボットWebhookへ送信する。

const MENU_ID = "lark-quick-send";
const URL_PATTERN = /https?:\/\/[^\s<>"')\]]+/;

chrome.runtime.onInstalled.addListener(() => {
  // reason:"update"（拡張の更新）でもonInstalledは発火し、Chromeに残る同一IDのメニューと
  // 衝突してlastErrorが発生するため、作成前に必ずremoveAllして冪等性を保つ。
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_ID,
      title: "Larkチャットへ送信",
      contexts: ["selection", "link"]
    });
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId !== MENU_ID) {
    return;
  }

  const text = extractPayload(info);

  if (!text) {
    notify(
      "Lark クイック送信",
      "テキストまたはリンクを選択してから右クリックしてください。"
    );
    return;
  }

  sendToLark(text);
});

// 右クリック情報から送信すべきテキストを抽出する。
function extractPayload(info) {
  if (info.linkUrl) {
    return info.linkUrl;
  }

  const selection = (info.selectionText || "").trim();
  if (!selection) {
    return "";
  }

  const urlMatch = selection.match(URL_PATTERN);
  if (urlMatch) {
    return urlMatch[0];
  }

  return selection;
}

// 指定テキストをLarkカスタムボットWebhookへPOSTする。
async function sendToLark(text) {
  const { webhookUrl } = await chrome.storage.local.get("webhookUrl");

  if (!webhookUrl) {
    notify(
      "Lark クイック送信",
      "設定画面でLarkのWebhook URLを登録してください。"
    );
    chrome.runtime.openOptionsPage();
    return;
  }

  try {
    const res = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ msg_type: "text", content: { text } })
    });

    const json = await res.json().catch(() => ({}));

    if (!res.ok || (json && json.code !== undefined && json.code !== 0)) {
      const reason = (json && json.msg) || `HTTPステータス ${res.status}`;
      notify("Lark クイック送信 - 送信失敗", `送信に失敗しました: ${reason}`);
      return;
    }

    notify("Lark クイック送信 - 送信成功", buildSuccessMessage(text));
  } catch (err) {
    const reason = err && err.message ? err.message : String(err);
    notify("Lark クイック送信 - 送信失敗", `送信に失敗しました: ${reason}`);
  }
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
