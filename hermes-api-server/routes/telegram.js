// hermes-api-server/routes/telegram.js
// Hermes Telegram Bot — KClaw AI Assistant + Bridge
require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const { chat } = require('../utils/chat-engine');
const { enhance, ENGINE_PROFILES } = require('../utils/prompt-engine');
const { receiveFromTelegram } = require('./telegram-bridge');

const TOKEN = process.env.TELEGRAM_BOT_TOKEN || '8313258482:AAGvwx2T_YOmQPQqgUnLT5mzuB9RusHvkCg';
const NGROK_URL = process.env.NGROK_URL || 'http://localhost:3001';

let bot = null;

// 對話歷史
const conversationHistory = new Map();
const MAX_HISTORY = 20;

function addToHistory(chatId, role, content) {
  if (!conversationHistory.has(chatId)) conversationHistory.set(chatId, []);
  const history = conversationHistory.get(chatId);
  history.push({ role, content, timestamp: Date.now() });
  while (history.length > MAX_HISTORY) history.shift();
}

function getHistory(chatId) { return conversationHistory.get(chatId) || []; }

function getBot() {
  if (!bot) {
    bot = new TelegramBot(TOKEN, { polling: true });
    console.log('🤖 Telegram Bot 已啟動！');

    // ── Commands ──
    bot.onText(/\/start/, (msg) => {
      bot.sendMessage(msg.chat.id,
        '🐯 嗨！我是 KClaw，Kent & KClaw Studio 的 AI 助手。\n\n' +
        '我能幫你：\n🎵 生成音樂 — /generate music\n🔧 AI 引擎 — /engines\n💬 直接聊天 — 打字就好\n\n完整指令：/help'
      );
    });

    bot.onText(/\/help/, (msg) => {
      bot.sendMessage(msg.chat.id,
        '📋 指令：\n/start — 歡迎\n/help — 幫助\n/status — 系統狀態\n/engines — AI 引擎（互動按鈕）\n/generate music [描述] — 生成音樂\n/clear — 清除對話歷史\n\n💡 直接打字我也會回！'
      );
    });

    bot.onText(/\/status/, (msg) => {
      const up = Math.floor(process.uptime());
      const h = Math.floor(up/3600), m = Math.floor((up%3600)/60), s = up%60;
      bot.sendMessage(msg.chat.id,
        `✅ 系統運行中\n⏱️ ${h}h ${m}m ${s}s\n🕐 ${new Date().toLocaleString('zh-TW',{timeZone:'Asia/Taipei'})}\n🐯 Hermes API v1.0.0`
      );
    });

    // /engines — Inline Keyboard
    bot.onText(/\/engines/, (msg) => {
      bot.sendMessage(msg.chat.id, '🔧 選擇一個 AI 引擎：', {
        reply_markup: {
          inline_keyboard: [
            [{ text: '🎵 ToneForge', callback_data: 'engine_toneforge' }, { text: '🎬 WireVision', callback_data: 'engine_wirevision' }],
            [{ text: '🖼️ FrameForge', callback_data: 'engine_frameforge' }, { text: '📸 SnapForge', callback_data: 'engine_snapforge' }],
            [{ text: '📖 ComicForge', callback_data: 'engine_comicforge' }]
          ]
        }
      });
    });

    bot.onText(/\/clear/, (msg) => {
      conversationHistory.delete(msg.chat.id);
      bot.sendMessage(msg.chat.id, '✅ 對話歷史已清除');
    });

    bot.onText(/\/generate music (.+)/, async (msg, match) => {
      await handleMusicGeneration(bot, msg.chat.id, match[1]);
    });

    // ── Callback Query（按鈕）──
    bot.on('callback_query', async (query) => {
      const chatId = query.message.chat.id;
      const data = query.data;
      if (data.startsWith('engine_')) {
        const engine = data.replace('engine_', '');
        const profile = ENGINE_PROFILES[engine];
        if (profile) {
          let text = `🔧 ${profile.name}\n${'─'.repeat(20)}\n📝 ${profile.description}\n`;
          if (profile.styles) text += `\n🎨 風格：${profile.styles.slice(0,6).join(', ')}`;
          if (profile.moods) text += `\n🎭 氛圍：${profile.moods.slice(0,6).join(', ')}`;
          if (profile.motions) text += `\n🎞️ 動態：${profile.motions.join(', ')}`;
          text += '\n\n💡 直接描述你想要的，我會自動用這個引擎！';
          await bot.answerCallbackQuery(query.id, { text: `已選擇 ${profile.name}` });
          await bot.sendMessage(chatId, text);
        }
      }
    });

    // ── 文字訊息 ──
    bot.on('message', async (msg) => {
      const chatId = msg.chat.id;
      const text = msg.text;
      if (!text || text.startsWith('/')) return;

      // 群組過濾：只在被 @mention 時回覆
      const isGroup = msg.chat.type === 'group' || msg.chat.type === 'supergroup';
      if (isGroup) {
        const botUsername = (await bot.getMe()).username.toLowerCase();
        const isMentioned = text.toLowerCase().includes(`@${botUsername}`) ||
          (msg.entities || []).some(e =>
            (e.type === 'mention' || e.type === 'text_mention') &&
            e.offset === 0 && text.substring(e.offset, e.offset + e.length).toLowerCase() === `@${botUsername}`
          );
        if (!isMentioned) return;
      }

      // ★ 橋接：同步到 KClaw Agent
      receiveFromTelegram(chatId, text, msg.from?.username || 'unknown');
      addToHistory(chatId, 'user', text);

      try {
        await bot.sendChatAction(chatId, 'typing');
        const analysis = enhance(text);
        const intent = analysis.intent;

        let reply = '';
        if (intent.engine && intent.engine !== 'undetected') {
          const rec = analysis.recommendation;
          reply = `🎯 偵測到你想用 ${ENGINE_PROFILES[rec.engine]?.name || rec.engine}！\n\n`;
          if (rec.body) {
            if (rec.body.style) reply += `• 風格：${rec.body.style}\n`;
            if (rec.body.mood) reply += `• 氛圍：${rec.body.mood}\n`;
            if (rec.body.duration) reply += `• 時長：${rec.body.duration}s\n`;
          }
          if (intent.engine === 'toneforge') reply += `\n🎵 直接生成：/generate music ${text}`;
          if (analysis.alternatives.length > 0) {
            reply += '\n\n🔄 也可以考慮：';
            analysis.alternatives.forEach(a => { reply += `\n• ${ENGINE_PROFILES[a.engine]?.name||a.engine} — ${a.reason}`; });
          }
        } else {
          const result = chat(text, { platform:'telegram', username:msg.from?.username, chatId });
          reply = result.response || '';
          if (result.tip) reply += '\n\n' + result.tip;
          if (result.suggestions) reply += '\n\n💡 試試：\n' + result.suggestions.map(s=>'• '+s).join('\n');
        }

        addToHistory(chatId, 'assistant', reply);
        await bot.sendMessage(chatId, reply.substring(0, 4096));
      } catch (err) {
        console.error('[Telegram] Error:', err.message);
        await bot.sendMessage(chatId, '❌ 出錯了，請稍後再試');
      }
    });

    // ── 圖片 ──
    bot.on('photo', async (msg) => {
      const chatId = msg.chat.id;

      // 群組過濾：只在 @mention 時處理圖片
      const isGroup = msg.chat.type === 'group' || msg.chat.type === 'supergroup';
      if (isGroup) {
        const caption = msg.caption || '';
        const botUsername = (await bot.getMe()).username.toLowerCase();
        const isMentioned = caption.toLowerCase().includes(`@${botUsername}`) ||
          (msg.caption_entities || []).some(e =>
            (e.type === 'mention' || e.type === 'text_mention') &&
            caption.substring(e.offset, e.offset + e.length).toLowerCase() === `@${botUsername}`
          );
        if (!isMentioned) return;
      }
      try {
        const photo = msg.photo[msg.photo.length - 1];
        const fileLink = await bot.getFileLink(photo.file_id);
        const caption = msg.caption || '';
        receiveFromTelegram(chatId, `[圖片: ${caption||'無描述'}]`, msg.from?.username||'?');
        let reply = `📷 收到圖片！\n🔗 ${fileLink}\n\n💡 加上描述我幫你推薦引擎！`;
        await bot.sendMessage(chatId, reply);
      } catch (err) {
        await bot.sendMessage(chatId, '❌ 圖片處理出錯');
      }
    });

    // ── 錯誤處理 ──
    bot.on('polling_error', (err) => {
      console.error('[Telegram] Polling error:', err.code, err.message);
      if (err.code === 'EFATAL' || err.code === 'ETIMEDOUT') {
        console.log('[Telegram] Restarting in 5s...');
        setTimeout(() => { bot.stopPolling(); bot.startPolling(); }, 5000);
      }
    });
  }
  return bot;
}

// ── 音樂生成 ──
async function handleMusicGeneration(bot, chatId, description) {
  await bot.sendChatAction(chatId, 'record_voice');
  try {
    const analysis = enhance(description);
    const body = analysis.recommendation.body || {};
    const style = body.style || 'Lofi Hip Hop', mood = body.mood || 'chill vibes', duration = body.duration || 15;
    await bot.sendMessage(chatId, `🎵 生成中...\n風格：${style}\n氛圍：${mood}\n時長：${duration}s`);

    const http = require('http');
    const payload = JSON.stringify({ style, mood, duration });
    const result = await new Promise((resolve, reject) => {
      const req = http.request({ hostname:'127.0.0.1', port: process.env.HERMES_PORT||3001, path:'/api/hermes/music/generate', method:'POST', headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(payload)} }, (res) => {
        let d=''; res.on('data',c=>d+=c); res.on('end',()=>{try{resolve(JSON.parse(d))}catch{reject(new Error('bad response'))}});
      });
      req.on('error', reject); req.write(payload); req.end();
    });

    if (result.success && result.audioUrl) {
      await bot.sendAudio(chatId, `${NGROK_URL}${result.audioUrl}`, { caption: `🎵 ${style} | ${mood} | ${duration}s` });
    } else {
      await bot.sendMessage(chatId, '⚠️ 音樂生成失敗');
    }
  } catch (err) {
    console.error('[Telegram] Music error:', err.message);
    await bot.sendMessage(chatId, '❌ 音樂生成出錯');
  }
}

function stopBot() {
  if (bot) { bot.stopPolling(); bot = null; console.log('🛑 Telegram Bot 已停止'); }
}

module.exports = { getBot, stopBot, getHistory, addToHistory };
