// Hermes Chat Engine
const { enhance } = require('./prompt-engine');
const FAQ_RESPONSES = {
  '怎麼用': { answer:'三步驟搞定：\n1️⃣ 選擇引擎\n2️⃣ 輸入描述\n3️⃣ 點擊生成', tip:'💡 描述越詳細，結果越好！' },
  '價格': { answer:'🆓 Free：$0/月\n⭐ Pro：$15/月\n🏢 Enterprise：客製方案', tip:'💡 先用免費方案試試！' },
  '音樂': { answer:'🎵 ToneForge - AI 配樂引擎，輸入描述即可生成音樂', tip:'💡 描述場景和心情效果最好！' },
  '影片': { answer:'🎬 WireVision - AI MV 引擎，上傳音樂自動生成同步影片', tip:'💡 搭配 ToneForge 效果最棒！' },
  '動畫': { answer:'🖼️ FrameForge - 圖片變動畫引擎', tip:'💡 高解析度圖片效果更好！' },
};
function findBestMatch(input) { const l=input.toLowerCase(); for (const[k,r] of Object.entries(FAQ_RESPONSES)) if (l.includes(k)) return r; return null; }
function chat(message, context={}) {
  const faq = findBestMatch(message);
  if (faq) return { type:'faq', response:faq.answer, tip:faq.tip, timestamp:new Date().toISOString() };
  const enhancement = enhance(message);
  if (enhancement.intent.engine) return { type:'enhancement', response:`目標引擎：${enhancement.recommendation.engine}`, recommendation:enhancement.recommendation, alternatives:enhancement.alternatives, intent:enhancement.intent, timestamp:new Date().toISOString() };
  return { type:'general', response:'我是 KClaw 🐯 可以幫你分析需求、推薦引擎、優化提示詞', suggestions:['幫我做一首放鬆的音樂','我想把照片變成動畫','推薦適合做產品影片的風格'], timestamp:new Date().toISOString() };
}
module.exports = { chat, findBestMatch, FAQ_RESPONSES };
