(function(){
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
  const path = (location.pathname.split('/').pop() || 'index.html').toLowerCase();

  const shared = {
    en: { langLabel: '中文' },
    zh: { langLabel: 'EN' }
  };

  const pages = {
    'index.html': {
      en: {
        nav:['Home','About','Focus','Projects','Team','Contact','Products'],
        eyebrow:'Creative software, AI tools, and experiments',
        title:'Building two focused products under one studio.',
        lead:'Kent & KClaw Studio is a creative tech studio building separate products with different jobs to do. ToneForge focuses on AI music generation for creators and brands. The WireVision product focuses on turning songs into short-form videos faster.',
        heroButtons:['Explore ToneForge','Launch App','Explore WireVision'],
        studio:'Studio direction',
        studioBullets:['One studio brand, two distinct product stories','ToneForge for AI music generation','WireVision for short-form video creation','Clearer positioning, clearer navigation, clearer growth path'],
        sectionTag:'Separate products, separate value propositions',
        product1:'An AI music product for creators, editors, and brands that need fast, usable music for shorts, ads, launches, and content workflows.',
        product2:'A separate product that turns songs into short videos with beat sync, templates, subtitle motion, and export presets for TikTok, Reels, and Shorts.',
        cardPs:['Learn what the studio stands for, how it thinks, and why it builds what it builds.','See the creative, technical, and product areas the studio is currently investing in.','Browse the current products and the direction of future experiments across the studio.'],
        ctaTitle:'The homepage now frames the studio around two products',
        ctaText:'Instead of blending everything into one offer, the front page now makes the split clear: ToneForge and WireVision are related, but they are not the same product.',
        ctaButtons:['See all projects','Contact']
      },
      zh: {
        nav:['首頁','關於','方向','專案','團隊','聯絡','產品'],
        eyebrow:'創意軟體、AI 工具與實驗',
        title:'在同一個工作室下，打造兩個明確聚焦的產品。',
        lead:'Kent & KClaw Studio 是一個創意科技工作室，正在打造兩條不同的產品線。ToneForge 專注在為創作者與品牌生成 AI 音樂；WireVision 則專注把歌曲更快轉成短影音內容。',
        heroButtons:['探索 ToneForge','開啟 App','探索 WireVision'],
        studio:'工作室方向',
        studioBullets:['一個工作室品牌，兩個清楚分開的產品故事','ToneForge：AI 音樂生成','WireVision：短影音生成','定位更清楚、導覽更清楚、成長路徑更清楚'],
        sectionTag:'產品分開，價值主張也分開',
        product1:'這是一個給創作者、剪輯師與品牌使用的 AI 音樂產品，能更快產出適合 Shorts、廣告、發表與內容流程的可用音樂。',
        product2:'這是一個獨立產品，能把歌曲轉成短影片，包含節拍同步、模板、字幕動態與 TikTok / Reels / Shorts 匯出預設。',
        cardPs:['了解工作室的理念、思考方式，以及它為何打造這些產品。','看看工作室目前投入的創意、技術與產品方向。','瀏覽現有產品與未來實驗方向。'],
        ctaTitle:'首頁現在清楚地用兩個產品來呈現工作室',
        ctaText:'不再把所有東西混成同一個提案，首頁現在直接說清楚：ToneForge 和 WireVision 彼此相關，但不是同一個產品。',
        ctaButtons:['查看所有專案','聯絡']
      }
    },
    'toneforge.html': {
      en: {
        nav:['← Studio','Demo','Features','Get Access'],
        eyebrow:'AI music for creators, ads, and content',
        title:'Generate short-form music in minutes.',
        lead:'ToneForge is the product page. The web app now lives on its own page so the product and the tool stay cleanly separated.',
        heroButtons:['Launch App','Join Early Access'],
        heroCard:'Current app scope',
        statLabels:['vibe + use case','demo generation flow','real API integration'],
        featuresTitle:'What ToneForge is aiming to do',
        featuresLead:'Start narrow, prove value, then grow.',
        features:[['Prompt + vibe input','Describe the sound you want and quickly move to candidate tracks.'],['Short-form ready','Made for quick outputs that fit reels, shorts, and promo edits.'],['Creator and brand use','Useful for ads, launches, mood tracks, and content production.']],
        ctaTitle:'Want the real version?', ctaText:'Join early access while the demo evolves into a real product.', ctaButtons:['Join Early Access','Back to Projects']
      },
      zh: {
        nav:['← 工作室','示範','功能','取得資格'],
        eyebrow:'給創作者、廣告與內容工作的 AI 音樂',
        title:'幾分鐘內生成短內容用音樂。',
        lead:'ToneForge 這頁是產品頁，實際 web app 已經獨立出去，讓產品敘事和工具體驗清楚分開。',
        heroButtons:['開啟 App','加入早期名單'],
        heroCard:'目前 App 範圍',
        statLabels:['vibe + 用途','demo 生成流程','之後接真 API'],
        featuresTitle:'ToneForge 想解決的事',
        featuresLead:'先聚焦、先證明價值，再逐步擴張。',
        features:[['Prompt + vibe 輸入','描述你要的聲音，快速拿到候選方向。'],['短影音就緒','為 reels、shorts 與 promo 剪輯而設計。'],['創作者與品牌都能用','適合廣告、發表、情境音樂與內容製作。']],
        ctaTitle:'想看真正版本？', ctaText:'趁 demo 持續進化成產品前，先加入早期名單。', ctaButtons:['加入早期名單','返回專案']
      }
    },
    'toneforge-app.html': {
      en: {
        nav:['← Back to ToneForge','WireVision'],
        title:'ToneForge App',
        lead:'A no-paid-API prototype for generating usable music options for short videos, ads, and creator workflows. Built around briefs, variants, selection, and reusable concepts instead of pretending to be a full song-generation platform.',
        labels:['Create brief','Creative brief','Use case','Duration','Mood','Energy','Generate Variants','Recent briefs','Queue','Version results','No variants yet. Start with a creative brief.','Workspace','Status','Model','Brief captured','Variants scored','Best fit selected','Credits','local demo runs left','Track detail','Selected variant','No variant selected','Library'],
        options:{useCase:['Short video','Ad / brand','Creator content'],duration:['15s','30s','60s'],mood:['Glossy','Cinematic','Luxury','Hype','Chill'],energy:['Low','Medium','High']}
      },
      zh: {
        nav:['← 返回 ToneForge','WireVision'],
        title:'ToneForge App',
        lead:'這是一個不依賴付費 API 的原型，用來幫短影音、廣告與創作者流程生成可用的音樂方向。它強調 brief、變體、選擇與可重用概念，而不是假裝自己是完整歌曲平台。',
        labels:['建立 brief','創意 brief','用途','長度','情緒','能量','生成變體','最近 brief','佇列','版本結果','目前還沒有變體。先從一個創意 brief 開始。','工作區','狀態','模型','已接收 brief','已完成變體評分','已選出最佳方向','點數','本地 demo 剩餘次數','曲目細節','已選變體','尚未選擇變體','資料庫'],
        options:{useCase:['短影音','廣告 / 品牌','創作者內容'],duration:['15秒','30秒','60秒'],mood:['光澤感','電影感','高級感','熱血','輕鬆'],energy:['低','中','高']}
      }
    },
    'wirevision.html': {
      en: {
        nav:['← Studio','Features','Workflow','Pricing','FAQ','Get Access'],
        eyebrow:'Short-form video creation for TikTok, Reels, and Shorts',
        title:'Turn songs into scroll-stopping videos in minutes.',
        lead:'WireVision helps creators turn songs into short-form videos with AI beat sync, viral-ready templates, subtitle motion, and one-click exports for every platform that matters. Less editing. Faster drafts. More publishable content.',
        heroButtons:['Join Early Access','See Pricing','View GitHub']
      },
      zh: {
        nav:['← 工作室','功能','流程','價格','FAQ','取得資格'],
        eyebrow:'為 TikTok、Reels、Shorts 而生的短影音製作工具',
        title:'幾分鐘內把歌曲變成吸睛短影片。',
        lead:'WireVision 幫創作者把歌曲轉成短影音，包含 AI 節拍同步、短影音模板、字幕動態與一鍵匯出。少一點剪輯、快一點出稿、多一點能發布的內容。',
        heroButtons:['加入早期名單','查看價格','查看 GitHub']
      }
    }
  };

  function setText(el, value){ if(el && value != null) el.textContent = value; }
  function setHTML(el, value){ if(el && value != null) el.innerHTML = value; }

  function applyIndex(lang){
    const d = pages[path][lang];
    $$('.nav a').forEach((a,i)=> setText(a, d.nav[i] || a.textContent));
    setText($('.eyebrow'), d.eyebrow); setText($('.title'), d.title); setText($('.lead'), d.lead);
    $$('.hero .buttons .btn').forEach((b,i)=> setText(b,d.heroButtons[i]));
    setText($('.hero-card h3'), d.studio);
    $$('.hero-list li').forEach((li,i)=> setText(li,d.studioBullets[i]));
    setText($('.tag'), d.sectionTag);
    const cards = $$('.product-card'); if(cards[0]) setText($('p',cards[0]),d.product1); if(cards[1]) setText($('p',cards[1]),d.product2);
    $$('.grid .card p').forEach((p,i)=> setText(p,d.cardPs[i]));
    setText($('.cta h2'), d.ctaTitle); setText($('.cta p'), d.ctaText); $$('.cta .btn').forEach((b,i)=> setText(b,d.ctaButtons[i]));
  }

  function applyToneforge(lang){
    const d = pages[path][lang];
    $$('.nav a').forEach((a,i)=> setText(a, d.nav[i] || a.textContent));
    setText($('.eyebrow'), d.eyebrow); setText($('.title'), d.title); setText($('.lead'), d.lead);
    $$('.hero-actions .btn').forEach((b,i)=> setText(b,d.heroButtons[i]));
    setText($('.hero-card strong'), d.heroCard); $$('.stat-box span').forEach((s,i)=> setText(s,d.statLabels[i]));
    setText($('#features .section-head h2'), d.featuresTitle); setText($('#features .section-head p'), d.featuresLead);
    $$('#features .card').forEach((card,i)=> { setText($('h3',card), d.features[i][0]); setText($('p',card), d.features[i][1]); });
    setText($('.cta h2'), d.ctaTitle); setText($('.cta p'), d.ctaText); $$('.cta .btn').forEach((b,i)=> setText(b,d.ctaButtons[i]));
  }

  function applyToneforgeApp(lang){
    const d = pages[path][lang];
    $$('.nav a').forEach((a,i)=> setText(a, d.nav[i] || a.textContent));
    setText($('.title'), d.title); setText($('.lead'), d.lead);
    const labels = d.labels;
    const targets = [
      '.panel h3','label[for="prompt"]','label[for="useCase"]','label[for="duration"]','label[for="mood"]','label[for="energy"]','#generateBtn','.history h3','#queue.parentNode h3','.panel:nth-of-type(2) h3','#emptyResults','.mini-card:nth-of-type(1) h3','.status-box .small','.status-box:nth-of-type(2) .small','#stepPrompt','#stepGenerate','#stepReady','.mini-card:nth-of-type(2) h3','.credit-box .small','.mini-card:nth-of-type(3) h3','#detailPanel .small','#detailPanel strong','.mini-card:nth-of-type(4) h3'
    ];
    targets.forEach((sel,i)=> { const el=$(sel); if(el) setText(el, labels[i]); });
    ['useCase','duration','mood','energy'].forEach(key=> { const sel=$('#'+key); if(sel){ $$('#'+key+' option').forEach((o,i)=> setText(o, d.options[key][i])); } });
  }

  function applyWirevision(lang){
    const d = pages[path][lang];
    $$('.nav a').forEach((a,i)=> setText(a, d.nav[i] || a.textContent));
    setText($('.eyebrow'), d.eyebrow);
    const title = $('h1'); if(title){ title.innerHTML = lang==='zh' ? '幾分鐘內把歌曲變成 <span class="gradient-text">吸睛短影片</span>。' : 'Turn songs into <span class="gradient-text">scroll-stopping videos</span> in minutes.'; }
    setText($('.lead'), d.lead); $$('.hero-actions .btn').forEach((b,i)=> setText(b,d.heroButtons[i]));
  }

  function setLang(lang){
    localStorage.setItem('site-lang', lang);
    document.documentElement.lang = lang === 'zh' ? 'zh-Hant' : 'en';
    $$('[data-lang-toggle]').forEach(sel => { sel.innerHTML = `<option value="${lang}">${shared[lang].langLabel}</option><option value="${lang==='zh'?'en':'zh'}">${lang==='zh'?'EN':'中文'}</option>`; sel.value = lang; });
    if(!pages[path]) return;
    if(path==='index.html') applyIndex(lang);
    if(path==='toneforge.html') applyToneforge(lang);
    if(path==='toneforge-app.html') applyToneforgeApp(lang);
    if(path==='wirevision.html') applyWirevision(lang);
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    $$('[data-lang-toggle]').forEach(sel => sel.addEventListener('change', e => setLang(e.target.value)));
    setLang(localStorage.getItem('site-lang') || 'en');
  });
})();
