// Lark クイック送信 - background と options で共有するロジック。
// 送信先の保存形式・検証・送信処理をここに集約し、二重実装による齟齬を防ぐ。
//
// 【重要】このファイルは ES モジュールにしない。
// service worker を `"type": "module"` にすると、休止状態から
// イベント（contextMenus.onClicked 等）で起こされる際に、モジュール解決が
// 非同期で走る分だけリスナー登録が遅れ、そのイベントを取りこぼすことがある。
// 実際に v1.1.0 で module 化した結果、右クリックからの送信が動かなくなった。
// background.js からは importScripts()（同期実行）で読み込み、
// リスナーが確実に同期的に登録されるようにしている。

var LarkShared = (function () {
  "use strict";

  // manifest.json の host_permissions と一致するドメイン・Larkカスタムボットの
  // Webhookパス形式のみを許可する。ここを緩めると、host_permissions外のURLが
  // 「保存しました」と表示された後の実送信時にCORS/権限エラーで必ず失敗し、
  // 原因が伝わらないまま「送信に失敗しました」としか出ない事故につながる。
  const WEBHOOK_URL_RE =
    /^https:\/\/(open\.larksuite\.com|open\.feishu\.cn)\/open-apis\/bot\/v2\/hook\/[A-Za-z0-9-]+$/;

  const CHAT_NAME_MAX = 24;

  // 保存形式: chats = [{ id, name, url }, ...]
  // v1.0.0 は単一の webhookUrl(文字列) だったため、初回読み込み時に移行する。
  async function loadChats() {
    const stored = await chrome.storage.local.get(["chats", "webhookUrl"]);

    if (Array.isArray(stored.chats)) {
      return stored.chats;
    }

    // v1.0.0 からの移行: 既存の単一Webhookを1件目の送信先として引き継ぐ。
    if (typeof stored.webhookUrl === "string" && stored.webhookUrl) {
      const migrated = [
        { id: newChatId(), name: "送信先1", url: stored.webhookUrl }
      ];
      await chrome.storage.local.set({ chats: migrated });
      await chrome.storage.local.remove("webhookUrl");
      return migrated;
    }

    return [];
  }

  async function saveChats(chats) {
    await chrome.storage.local.set({ chats });
  }

  function newChatId() {
    return `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  // 入力値を検証する。問題があれば理由の文字列を、無ければ null を返す。
  function validateChat(name, url, existingChats, ignoreId) {
    const trimmedName = name.trim();
    const trimmedUrl = url.trim();

    if (!trimmedName) {
      return "チャット名を入力してください。";
    }
    if (trimmedName.length > CHAT_NAME_MAX) {
      return `チャット名は${CHAT_NAME_MAX}文字以内で入力してください。`;
    }
    if (!WEBHOOK_URL_RE.test(trimmedUrl)) {
      return "Larkのカスタムボット Webhook URL（https://open.larksuite.com/open-apis/bot/v2/hook/... 形式）を入力してください。";
    }

    const others = existingChats.filter((c) => c.id !== ignoreId);
    if (others.some((c) => c.name === trimmedName)) {
      return "同じ名前の送信先がすでに登録されています。";
    }
    if (others.some((c) => c.url === trimmedUrl)) {
      return "同じWebhook URLの送信先がすでに登録されています。";
    }

    return null;
  }

  // Webhookへテキストを送信する。成功なら {ok:true}、失敗なら {ok:false, reason}。
  async function postToWebhook(url, text) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msg_type: "text", content: { text } })
      });

      const json = await res.json().catch(() => ({}));

      if (!res.ok || (json && json.code !== undefined && json.code !== 0)) {
        return {
          ok: false,
          reason: (json && json.msg) || `HTTPステータス ${res.status}`
        };
      }

      return { ok: true };
    } catch (err) {
      return { ok: false, reason: err && err.message ? err.message : String(err) };
    }
  }

  return {
    WEBHOOK_URL_RE,
    CHAT_NAME_MAX,
    loadChats,
    saveChats,
    newChatId,
    validateChat,
    postToWebhook
  };
})();
