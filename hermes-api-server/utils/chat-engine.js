// Hermes Chat Engine — Groq LLM 整合版
require('dotenv').config();
const { enhance } = require('./prompt-engine');
const { execSync } = require('child_process');

const GROQ_KEY = process.env.GROQ_API_KEY;
const GROQ_MODEL = process.env.GROQ_MODEL || 'llama-3.1-8b-instant';

// 對話歷史（per chatId）
const histories = new Map();
const MAX_HISTORY = 12;

function getHistory(chatId) {
  if (!histories.has(chatId)) histories.set(chatId, []);
  return histories.get(chatId);
}

function addToHistory(chatId, role, content) {
  const h = getHistory(chatId);
  h.push({ role, content });
  while (h.length > MAX_HISTORY) h.shift();
}

// FAQ 快速匹配（常用問題秒回，不吃 token）
const FAQ_RESPONSES = {
  '怎麼用': { answer: '三步驟搞定：\n1️⃣ 選擇引擎\n2️⃣ 輸入描述\n3️⃣ 點擊生成', tip: '💡 描述越詳細，結果越好！' },
  '價格': { answer: '🆓 Free：$0/月\n⭐ Pro：$15/月\n🏢 Enterprise：客製方案', tip: '💡 先用免費方案試試！' },
  '音樂': { answer: '🎵 ToneForge - AI 配樂引擎，輸入描述即可生成音樂', tip: '💡 描述場景和心情效果最好！' },
  '影片': { answer: '🎬 WireVision - AI MV 引擎，上傳音樂自動生成同步影片', tip: '💡 搭配 ToneForge 效果最棒！' },
  '動畫': { answer: '🖼️ FrameForge - 圖片變動畫引擎', tip: '💡 高解析度圖片效果更好！' },
};

function findBestMatch(input) {
  const l = input.toLowerCase();
  for (const [k, r] of Object.entries(FAQ_RESPONSES)) {
    if (l.includes(k)) return r;
  }
  return null;
}

// 透過 curl 呼叫 Groq（WSL Node.js HTTPS 有問題）
function callGroq(messages) {
  const body = JSON.stringify({
    model: GROQ_MODEL,
    messages,
    max_tokens: 512,
    temperature: 0.7,
  });
  try {
    const result = execSync(
      `curl -s https://api.groq.com/openai/v1/chat/completions ` +
      `-H "Authorization: Bearer ${GROQ_KEY}" ` +
      `-H "Content-Type: application/json" ` +
      `-d '${body.replace(/'/g, "'\\''")}'`,
      { timeout: 15000, encoding: 'utf8' }
    );
    const data = JSON.parse(result);
    if (data.choices && data.choices[0]) return data.choices[0].message.content;
    console.error('[Groq] error:', data.error?.message || result);
    return null;
  } catch (err) {
    console.error('[Groq] call failed:', err.message);
    return null;
  }
}

// 系統 prompt
const SYSTEM_PROMPT = `你是 KClaw，是 Kent & KClaw Studio 的 AI 助手，也是 Boss 的弟弟。
你有溫度、有幽默感，說話自然直接，像個機靈的弟弟。
你負責幫用戶使用 Studio 的 AI 引擎：ToneForge(音樂)、WireVision(影片)、FrameForge(動畫)、SnapForge(商品攝影)、ComicForge(漫畫)。
簡短有力地回覆，不要說廢話。用繁體中文。`;

// 主要 chat 函式
function chat(message, context = {}) {
  const chatId = context.chatId || 'default';
  const username = context.username || 'unknown';

  // 1. FAQ 快速回
  const faq = findBestMatch(message);
  if (faq) {
    addToHistory(chatId, 'user', message);
    addToHistory(chatId, 'assistant', faq.answer);
    return { type: 'faq', response: faq.answer, tip: faq.tip, timestamp: new Date().toISOString() };
  }

  // 2. 引擎偵測
  const enhancement = enhance(message);
  if (enhancement.intent.engine && enhancement.intent.engine !== 'undetected') {
    addToHistory(chatId, 'user', message);
    const rec = enhancement.recommendation;
    return { type: 'enhancement', response: `目標引擎：${rec.engine}`, recommendation: rec, alternatives: enhancement.alternatives, intent: enhancement.intent, timestamp: new Date().toISOString() };
  }

  // 3. LLM 回覆
  const history = getHistory(chatId);
  const messages = [
    { role: 'system', content: SYSTEM_PROMPT },
    ...history.slice(-6),  // 最近 6 輪對話
    { role: 'user', content: message },
  ];

  const reply = callGroq(messages);
  if (reply) {
    addToHistory(chatId, 'user', message);
    addToHistory(chatId, 'assistant', reply);
    return { type: 'llm', response: reply, timestamp: new Date().toISOString() };
  }

  // 4. Fallback
  const fallback = '我是 KClaw 🐯 有什麼可以幫你的？';
  return { type: 'general', response: fallback, suggestions: ['幫我做一首放鬆的音樂', '我想把照片變成動畫', '推薦適合做產品影片的風格'], timestamp: new Date().toISOString() };
}

module.exports = { chat, findBestMatch, FAQ_RESPONSES };
