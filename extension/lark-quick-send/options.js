// Lark クイック送信 - 設定画面（送信先チャットの追加・テスト・削除）

// shared.js は options.html で先に読み込まれる通常スクリプト。
// （service worker 側と実装を共有するため ES モジュールにはしていない）
const {
  loadChats,
  saveChats,
  newChatId,
  validateChat,
  postToWebhook,
  CHAT_NAME_MAX
} = LarkShared;

const listEl = document.getElementById("list");
const countEl = document.getElementById("count");
const nameInput = document.getElementById("chatName");
const urlInput = document.getElementById("chatUrl");
const addBtn = document.getElementById("addBtn");
const statusEl = document.getElementById("status");

let chats = [];
// 編集中の送信先ID。null のときは全カードが通常表示。
let editingId = null;

document.addEventListener("DOMContentLoaded", async () => {
  chats = await loadChats();
  render();
});

addBtn.addEventListener("click", async () => {
  const name = nameInput.value.trim();
  const url = urlInput.value.trim();

  const error = validateChat(name, url, chats, null);
  if (error) {
    showStatus(error, "error");
    return;
  }

  chats = [...chats, { id: newChatId(), name, url }];
  await saveChats(chats);

  nameInput.value = "";
  urlInput.value = "";
  render();
  showStatus(`「${name}」を追加しました。`, "success");
});

// 一覧を描画する。textContent で入れるため、チャット名によるHTML混入は起こらない。
function render() {
  countEl.textContent = chats.length > 0 ? `${chats.length}件` : "";
  listEl.replaceChildren();

  if (chats.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "送信先がまだありません。下のフォームから追加してください。";
    listEl.append(empty);
    return;
  }

  for (const chat of chats) {
    listEl.append(
      chat.id === editingId ? buildEditCard(chat) : buildChatCard(chat)
    );
  }
}

function buildChatCard(chat) {
  const card = document.createElement("div");
  card.className = "chat";

  const name = document.createElement("p");
  name.className = "chat-name";
  name.textContent = chat.name;

  const url = document.createElement("p");
  url.className = "chat-url";
  url.textContent = shortenUrl(chat.url);
  url.title = chat.url;

  const actions = document.createElement("div");
  actions.className = "chat-actions";

  const testBtn = document.createElement("button");
  testBtn.type = "button";
  testBtn.className = "btn-quiet";
  testBtn.textContent = "テスト送信";
  testBtn.addEventListener("click", () => testChat(chat, testBtn));

  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "btn-quiet";
  editBtn.textContent = "編集";
  editBtn.addEventListener("click", () => {
    editingId = chat.id;
    render();
    showStatus("", "");
  });

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "btn-quiet btn-danger";
  deleteBtn.textContent = "削除";
  deleteBtn.addEventListener("click", () => deleteChat(chat));

  actions.append(testBtn, editBtn, deleteBtn);
  card.append(name, url, actions);
  return card;
}

// 編集中のカード。名前とURLをその場で直せるようにする。
function buildEditCard(chat) {
  const card = document.createElement("div");
  card.className = "chat is-editing";

  const nameField = document.createElement("div");
  nameField.className = "field";
  const nameLabel = document.createElement("label");
  nameLabel.textContent = "チャット名";
  nameLabel.htmlFor = "editName";
  const nameInputEl = document.createElement("input");
  nameInputEl.type = "text";
  nameInputEl.id = "editName";
  nameInputEl.maxLength = CHAT_NAME_MAX;
  nameInputEl.value = chat.name;
  nameField.append(nameLabel, nameInputEl);

  const urlField = document.createElement("div");
  urlField.className = "field";
  const urlLabel = document.createElement("label");
  urlLabel.textContent = "Webhook URL";
  urlLabel.htmlFor = "editUrl";
  const urlInputEl = document.createElement("input");
  urlInputEl.type = "text";
  urlInputEl.id = "editUrl";
  urlInputEl.value = chat.url;
  urlField.append(urlLabel, urlInputEl);

  const actions = document.createElement("div");
  actions.className = "chat-actions";

  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "btn-quiet btn-accent";
  saveBtn.textContent = "保存";
  saveBtn.addEventListener("click", () =>
    saveEdit(chat, nameInputEl.value, urlInputEl.value)
  );

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "btn-quiet";
  cancelBtn.textContent = "キャンセル";
  cancelBtn.addEventListener("click", () => {
    editingId = null;
    render();
    showStatus("", "");
  });

  actions.append(saveBtn, cancelBtn);
  card.append(nameField, urlField, actions);
  return card;
}

async function saveEdit(chat, rawName, rawUrl) {
  const name = rawName.trim();
  const url = rawUrl.trim();

  // 自分自身は重複判定から除外する。
  const error = validateChat(name, url, chats, chat.id);
  if (error) {
    showStatus(error, "error");
    return;
  }

  chats = chats.map((c) => (c.id === chat.id ? { ...c, name, url } : c));
  await saveChats(chats);

  editingId = null;
  render();
  showStatus(`「${name}」を更新しました。`, "success");
}

// Webhook URL は末尾のトークンが長いため、一覧では省略して表示する。
function shortenUrl(url) {
  const withoutScheme = url.replace(/^https:\/\//, "");
  return withoutScheme.length > 46
    ? `${withoutScheme.slice(0, 34)}...${withoutScheme.slice(-8)}`
    : withoutScheme;
}

async function testChat(chat, button) {
  button.disabled = true;
  showStatus(`「${chat.name}」へテスト送信中...`, "pending");

  const result = await postToWebhook(
    chat.url,
    "【Lark クイック送信】接続テストです。"
  );

  button.disabled = false;

  if (!result.ok) {
    showStatus(`「${chat.name}」へのテスト送信に失敗しました: ${result.reason}`, "error");
    return;
  }

  showStatus(`「${chat.name}」へテスト送信しました。チャットを確認してください。`, "success");
}

async function deleteChat(chat) {
  // 削除は取り消せないため、必ず確認を挟む。
  if (!confirm(`送信先「${chat.name}」を削除します。よろしいですか？`)) {
    return;
  }

  chats = chats.filter((c) => c.id !== chat.id);
  if (editingId === chat.id) {
    editingId = null;
  }
  await saveChats(chats);
  render();
  showStatus(`「${chat.name}」を削除しました。`, "success");
}

function showStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = kind || "";
}
