// hermes-api-server/routes/telegram-bridge.js
// 雙向橋接：Telegram ↔ CLI/KClaw Agent
// 使用 curl 呼叫 Telegram API（WSL Node.js HTTPS 有問題）
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const BRIDGE_FILE = path.join(__dirname, '..', 'telegram-bridge.json');

// ═══════════════════════════════════════
// 橋接狀態檔案
// ═══════════════════════════════════════
function loadBridge() {
  try { return JSON.parse(fs.readFileSync(BRIDGE_FILE, 'utf8')); }
  catch { return { chatId: null, connected: false, messages: [] }; }
}

function saveBridge(data) {
  fs.writeFileSync(BRIDGE_FILE, JSON.stringify(data, null, 2));
}

// ═══════════════════════════════════════
// Telegram API（curl）
// ═══════════════════════════════════════
function telegramAPI(method, params = {}) {
  const dataStr = Object.entries(params)
    .map(([k, v]) => `--data-urlencode "${k}=${v}"`)
    .join(' ');
  try {
    const result = execSync(
      `curl -s "https://api.telegram.org/bot${TOKEN}/${method}" ${dataStr}`,
      { timeout: 15000, encoding: 'utf8' }
    );
    return JSON.parse(result);
  } catch (err) {
    console.error('[Bridge] telegramAPI error:', err.message);
    return { ok: false, error: err.message };
  }
}

// ═══════════════════════════════════════
// CLI → Telegram
// ═══════════════════════════════════════
function sendToTelegram(text) {
  const bridge = loadBridge();
  if (!bridge.chatId) {
    return { ok: false, error: 'not connected — 請先在 Telegram 傳訊息給 @KentCclawbot' };
  }

  const result = telegramAPI('sendMessage', {
    chat_id: bridge.chatId,
    text: `🤖 [KClaw Agent]\n${text}`
  });

  if (result.ok) {
    bridge.messages.push({ direction: 'agent→telegram', text, timestamp: Date.now() });
    saveBridge(bridge);
  }
  return result;
}

// ═══════════════════════════════════════
// Telegram → CLI
// ═══════════════════════════════════════
function receiveFromTelegram(chatId, text, username) {
  const bridge = loadBridge();
  if (!bridge.chatId) {
    bridge.chatId = chatId;
    bridge.connected = true;
    bridge.connectedAt = Date.now();
    console.log(`[Bridge] Telegram 已連接！chatId=${chatId} user=@${username}`);
  }
  bridge.messages.push({ direction: 'telegram→agent', chatId, username, text, timestamp: Date.now() });
  if (bridge.messages.length > 100) bridge.messages = bridge.messages.slice(-100);
  saveBridge(bridge);
  return bridge;
}

function getNewMessages(since = 0) {
  return loadBridge().messages.filter(m => m.direction === 'telegram→agent' && m.timestamp > since);
}

function getConnectionStatus() { return loadBridge(); }

module.exports = { sendToTelegram, receiveFromTelegram, getNewMessages, getConnectionStatus, telegramAPI, loadBridge, saveBridge };
