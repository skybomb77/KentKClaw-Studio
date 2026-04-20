// hermes-api-server/routes/telegram-bot2.js
// 第二個弟弟 KAhermesbot
require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const { receiveFromTelegram } = require('./telegram-bridge');

const TOKEN = process.env.TELEGRAM_BOT_TOKEN_2;
let bot2 = null;

function getBot2() {
  if (!bot2 && TOKEN) {
    bot2 = new TelegramBot(TOKEN, { polling: true });
    console.log('🤖 KAhermesbot 已啟動！');

    bot2.on('message', async (msg) => {
      const chatId = msg.chat.id;
      const text = msg.text;
      if (!text) return;

      // 同步到 bridge
      receiveFromTelegram(chatId, text, msg.from?.username || 'unknown');

      // 群組指令
      if (text === '/status') {
        await bot2.sendMessage(chatId, '✅ KAhermesbot 在線！');
      }
    });

    bot2.on('polling_error', (err) => {
      console.error('[KAhermesbot] Polling error:', err.code, err.message);
    });
  }
  return bot2;
}

function stopBot2() {
  if (bot2) { bot2.stopPolling(); bot2 = null; }
}

module.exports = { getBot2, stopBot2 };
