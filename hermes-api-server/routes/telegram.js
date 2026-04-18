const TelegramBot = require('node-telegram-bot-api');
const { chat } = require('../utils/chat-engine');

const TOKEN = process.env.TELEGRAM_BOT_TOKEN || '8313258482:AAGvwx2T_YOmQPQqgUnLT5mzuB9RusHvkCg';

let bot = null;

function getBot() {
  if (!bot) {
    bot = new TelegramBot(TOKEN, { polling: true });
    console.log('🤖 Telegram Bot 已啟動！');

    bot.on('message', async (msg) => {
      const chatId = msg.chat.id;
      const text = msg.text;
      if (!text) return;

      // Commands
      if (text === '/start') {
        await bot.sendMessage(chatId,
          '🐯 嗨！我是 KClaw，Hermes AI 助手。\n\n' +
          '直接跟我說話就好，我會幫你處理！\n\n' +
          '指令：\n' +
          '/start - 開始使用\n' +
          '/help - 幫助資訊\n' +
          '/status - 系統狀態'
        );
        return;
      }

      if (text === '/help') {
        await bot.sendMessage(chatId,
          '📋 Hermes AI 助手功能：\n\n' +
          '• 自然語言對話\n' +
          '• 智慧提示詞增強\n' +
          '• AI 引擎路由\n' +
          '• 音樂生成（即將推出）\n\n' +
          '直接輸入問題就可以開始！'
        );
        return;
      }

      if (text === '/status') {
        await bot.sendMessage(chatId,
          '✅ 系統運行中\n' +
          `🕐 ${new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' })}\n` +
          '🐯 Hermes API v1.0.0'
        );
        return;
      }

      // Chat
      try {
        await bot.sendChatAction(chatId, 'typing');

        const result = chat(text, {
          platform: 'telegram',
          username: msg.from?.username,
          chatId
        });

        let reply = result.response || '';
        if (result.tip) reply += '\n\n' + result.tip;
        if (result.suggestions) reply += '\n\n試試問：\n' + result.suggestions.map(s => '• ' + s).join('\n');

        await bot.sendMessage(chatId, reply.substring(0, 4096));
      } catch (err) {
        console.error('Telegram bot error:', err);
        await bot.sendMessage(chatId, '❌ 系統暫時無法回應，請稍後再試。');
      }
    });

    bot.on('polling_error', (err) => {
      console.error('Telegram polling error:', err.message);
    });
  }
  return bot;
}

function stopBot() {
  if (bot) {
    bot.stopPolling();
    bot = null;
    console.log('🛑 Telegram Bot 已停止');
  }
}

module.exports = { getBot, stopBot };
