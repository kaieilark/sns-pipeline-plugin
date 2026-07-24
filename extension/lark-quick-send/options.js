// Lark クイック送信 - 設定画面

// manifest.json の host_permissions と一致するドメイン・Larkカスタムボットの
// Webhookパス形式のみを許可する。ここを緩めると、host_permissions外のURLが
// 「保存しました」と表示された後の実送信時にCORS/権限エラーで必ず失敗し、
// 原因が伝わらないまま「送信に失敗しました」としか出ない事故につながる。
const URL_INPUT_RE = /^https:\/\/(open\.larksuite\.com|open\.feishu\.cn)\/open-apis\/bot\/v2\/hook\/[A-Za-z0-9-]+$/;

const webhookInput = document.getElementById("webhookUrl");
const saveBtn = document.getElementById("saveBtn");
const testBtn = document.getElementById("testBtn");
const statusEl = document.getElementById("status");

document.addEventListener("DOMContentLoaded", async () => {
  const { webhookUrl } = await chrome.storage.local.get("webhookUrl");
  if (webhookUrl) {
    webhookInput.value = webhookUrl;
  }
});

saveBtn.addEventListener("click", async () => {
  const url = webhookInput.value.trim();

  if (!URL_INPUT_RE.test(url)) {
    showStatus("Larkのカスタムボット Webhook URL（https://open.larksuite.com/open-apis/bot/v2/hook/... 形式）を入力してください", "error");
    return;
  }

  await chrome.storage.local.set({ webhookUrl: url });
  showStatus("保存しました。", "success");
});

testBtn.addEventListener("click", async () => {
  const url = webhookInput.value.trim();

  if (!URL_INPUT_RE.test(url)) {
    showStatus("Larkのカスタムボット Webhook URL（https://open.larksuite.com/open-apis/bot/v2/hook/... 形式）を入力してください", "error");
    return;
  }

  showStatus("テスト送信中...", "");

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        msg_type: "text",
        content: { text: "【Lark クイック送信】接続テストです。" }
      })
    });

    const json = await res.json().catch(() => ({}));

    if (!res.ok || (json && json.code !== undefined && json.code !== 0)) {
      const reason = (json && json.msg) || `HTTPステータス ${res.status}`;
      showStatus(`テスト送信に失敗しました: ${reason}`, "error");
      return;
    }

    showStatus("テスト送信に成功しました。チャットを確認してください。", "success");
  } catch (err) {
    const reason = err && err.message ? err.message : String(err);
    showStatus(`テスト送信に失敗しました: ${reason}`, "error");
  }
});

function showStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = kind || "";
}
