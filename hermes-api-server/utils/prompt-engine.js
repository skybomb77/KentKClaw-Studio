// Hermes Prompt Engine - 智慧提示詞增強核心
const ENGINE_PROFILES = {
  toneforge: { name: 'ToneForge', category: 'music', description: 'AI 配樂引擎',
    styles: ['Lofi Hip Hop','Techno','Cyberpunk','Cinematic','Epic','Acoustic','Jazz','Pop','Rock','Electronic'],
    moods: ['chill','energetic','melancholic','uplifting','dark','dreamy','aggressive','peaceful'] },
  wirevision: { name: 'WireVision', category: 'video', description: 'AI MV 影片引擎',
    styles: ['neon cyberpunk','vaporwave','minimalist','cinematic','abstract','retro','futuristic','nature'],
    prompts: ['highly detailed','masterpiece','best quality','smooth motion','vibrant colors'] },
  frameforge: { name: 'FrameForge', category: 'animation', description: 'AI 動畫引擎',
    styles: ['smooth','dynamic','subtle','dramatic','flowing','bouncy'], motions: ['Subtle','Normal','Dynamic'] },
  snapforge: { name: 'SnapForge', category: 'photo', description: 'AI 商品攝影',
    styles: ['studio white','lifestyle','minimalist','luxury','natural light','dramatic shadow'] },
  comicforge: { name: 'ComicForge', category: 'comic', description: 'AI 漫畫生成',
    styles: ['manga','webtoon','american comic','manhwa','watercolor','ink sketch'] },
};

const STYLE_KEYWORDS = {
  'lofi':'Lofi Hip Hop','放鬆':'Lofi Hip Hop','chill':'Lofi Hip Hop','咖啡':'Lofi Hip Hop',
  '電音':'Techno','techno':'Techno','派對':'Techno',
  '賽博':'Cyberpunk','cyberpunk':'Cyberpunk','科幻':'Cyberpunk',
  '電影':'Cinematic','cinematic':'Cinematic','史詩':'Epic','epic':'Epic',
  '原聲':'Acoustic','acoustic':'Acoustic','民謠':'Acoustic',
  '爵士':'Jazz','jazz':'Jazz','咖啡廳':'Jazz','cafe':'Jazz',
  '流行':'Pop','pop':'Pop','搖滾':'Rock','rock':'Rock','電子':'Electronic',
  '霓虹':'neon cyberpunk','蒸汽波':'vaporwave','極簡':'minimalist','復古':'retro','未來':'futuristic',
  '開心':'uplifting','快樂':'uplifting','憂鬱':'melancholy','悲傷':'melancholy',
  '黑暗':'dark','夢幻':'dreamy','激動':'energetic','平靜':'peaceful',
};

function parseIntent(text) {
  const lower = text.toLowerCase();
  const intent = { engine: null, style: null, mood: null, subject: text, duration: 15, ratio: '16:9' };
  if (lower.includes('音樂')||lower.includes('配樂')||lower.includes('歌')||lower.includes('beat')||lower.includes('music')||lower.includes('bgm')||lower.includes('樂')||lower.includes('曲')) intent.engine = 'toneforge';
  else if (lower.includes('影片')||lower.includes('mv')||lower.includes('video')||lower.includes('短片')||lower.includes('視頻')) intent.engine = 'wirevision';
  else if (lower.includes('動畫')||lower.includes('animation')||lower.includes('動態')||lower.includes('動起來')) intent.engine = 'frameforge';
  else if (lower.includes('商品')||lower.includes('產品')||lower.includes('照片')||lower.includes('photo')||lower.includes('攝影')||lower.includes('去背')) intent.engine = 'snapforge';
  else if (lower.includes('漫畫')||lower.includes('comic')||lower.includes('故事')||lower.includes('多格')) intent.engine = 'comicforge';
  for (const [keyword, mapped] of Object.entries(STYLE_KEYWORDS)) {
    if (lower.includes(keyword)) { if (!intent.style) intent.style = mapped; }
  }
  const durMatch = text.match(/(\d+)\s*[秒s]/);
  if (durMatch) intent.duration = Math.min(parseInt(durMatch[1]), 60);
  if (lower.includes('直式')||lower.includes('9:16')||lower.includes('tiktok')) intent.ratio = '9:16';
  else if (lower.includes('方形')||lower.includes('1:1')) intent.ratio = '1:1';
  return intent;
}

function enhance(input) {
  const intent = parseIntent(input);
  let recommendation = null, alternatives = [];
  switch (intent.engine) {
    case 'toneforge':
      recommendation = { engine:'toneforge', style: intent.style||'Lofi Hip Hop', mood: (intent.mood||'chill')+', professional studio mix', duration: intent.duration, apiEndpoint:'/api/forge-music', method:'POST',
        body:{ style:intent.style||'Lofi Hip Hop', mood:(intent.mood||'chill')+', professional studio mix', duration:intent.duration } };
      alternatives = [{engine:'wirevision',reason:'如果需要配上音樂的 MV'}]; break;
    case 'wirevision':
      recommendation = { engine:'wirevision', prompt:`masterpiece, best quality, highly detailed, ${intent.style||'neon cyberpunk'}, smooth motion, vibrant colors, cinematic lighting, 4k`, ratio:intent.ratio, apiEndpoint:'/api/generate-mv', method:'POST' };
      alternatives = [{engine:'toneforge',reason:'如果只需要音樂'},{engine:'frameforge',reason:'如果是靜態圖片轉動畫'}]; break;
    case 'frameforge':
      recommendation = { engine:'frameforge', prompt:`masterpiece, best quality, ${intent.style||'smooth flowing'} animation, dynamic, alive`, motion:intent.style==='dynamic'?'Dynamic':intent.style==='subtle'?'Subtle':'Normal', apiEndpoint:'/api/generate-img2vid', method:'POST' };
      alternatives = [{engine:'wirevision',reason:'如果是音樂配影片'}]; break;
    case 'snapforge': recommendation = {engine:'snapforge',style:intent.style||'studio white',apiEndpoint:'/snapforge.html',method:'redirect'}; break;
    case 'comicforge': recommendation = {engine:'comicforge',style:intent.style||'manga',apiEndpoint:'https://skybomb77.github.io/comicforge/',method:'redirect'}; break;
    default: recommendation = {engine:'undetected',message:'無法判斷目標引擎',suggestions:Object.values(ENGINE_PROFILES).map(e=>({engine:e.name,description:e.description}))};
  }
  return { input, intent, recommendation, alternatives, engines: ENGINE_PROFILES };
}

module.exports = { enhance, parseIntent, ENGINE_PROFILES, STYLE_KEYWORDS };
