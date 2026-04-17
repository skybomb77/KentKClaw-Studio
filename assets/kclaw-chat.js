// KClaw Chat Widget - AI Assistant for Kent & KClaw Studio
// Connects to Hermes API Server

(function() {
  'use strict';

  const CONFIG = {
    // Auto-detect: if on localhost use local, otherwise use tunnel
    apiUrl: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://127.0.0.1:3001'
      : 'https://nonchimeric-fabled-nila.ngrok-free.dev',
    botName: 'KClaw',
    botEmoji: '🐯',
    welcomeMsg: '嗨！我是 KClaw 🐯 你的 AI 創意助手。有什麼需要幫忙的嗎？',
    suggestions: [
      '🎵 做一首音樂',
      '🎬 做一個 MV',
      '🖼️ 圖片變動畫',
      '💡 推薦引擎',
      '💰 價格方案',
    ],
  };

  let isOpen = false;
  let messages = [];

  // Create widget HTML
  function createWidget() {
    const widget = document.createElement('div');
    widget.className = 'kclaw-widget';
    widget.innerHTML = `
      <div class="kclaw-panel" id="kclawPanel">
        <div class="kclaw-header">
          <div class="avatar">${CONFIG.botEmoji}</div>
          <div class="info">
            <h3>${CONFIG.botName}</h3>
            <p>AI Creative Assistant</p>
          </div>
          <div class="status"></div>
        </div>
        <div class="kclaw-messages" id="kclawMessages"></div>
        <div class="kclaw-suggestions" id="kclawSuggestions"></div>
        <div class="kclaw-input-area">
          <input type="text" id="kclawInput" placeholder="輸入你的創意想法..." autocomplete="off" />
          <button id="kclawSend">➤</button>
        </div>
      </div>
      <button class="kclaw-toggle" id="kclawToggle">
        🐯
        <span class="badge" id="kclawBadge">1</span>
      </button>
    `;
    document.body.appendChild(widget);

    // Load CSS
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = getAssetPath('kclaw-chat.css');
    document.head.appendChild(link);

    // Bind events
    document.getElementById('kclawToggle').addEventListener('click', togglePanel);
    document.getElementById('kclawSend').addEventListener('click', sendMessage);
    document.getElementById('kclawInput').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendMessage();
    });

    // Show welcome after a short delay
    setTimeout(() => {
      addBotMessage(CONFIG.welcomeMsg);
      showSuggestions(CONFIG.suggestions);
      // Flash the toggle
      document.getElementById('kclawBadge').classList.add('show');
    }, 1500);
  }

  function getAssetPath(filename) {
    // Try to detect the base path
    const scripts = document.querySelectorAll('script[src*="kclaw"]');
    if (scripts.length > 0) {
      return scripts[0].src.replace('kclaw-chat.js', filename);
    }
    // Fallback: use relative path from page
    const path = window.location.pathname;
    const base = path.substring(0, path.lastIndexOf('/') + 1);
    return base + 'assets/' + filename;
  }

  function togglePanel() {
    isOpen = !isOpen;
    const panel = document.getElementById('kclawPanel');
    const badge = document.getElementById('kclawBadge');
    panel.classList.toggle('open', isOpen);
    if (isOpen) {
      badge.classList.remove('show');
      document.getElementById('kclawInput').focus();
    }
  }

  function addBotMessage(text, extra = {}) {
    const container = document.getElementById('kclawMessages');
    const msg = document.createElement('div');
    msg.className = 'kclaw-msg bot';

    let html = text.replace(/\n/g, '<br>');
    if (extra.tip) {
      html += `<div class="tip">${extra.tip}</div>`;
    }
    if (extra.engine) {
      html += `<div class="kclaw-engine-card">
        <h4>🎯 推薦引擎：${extra.engine}</h4>
        ${extra.style ? `<p>風格：${extra.style}</p>` : ''}
        ${extra.endpoint ? `<p>API：${extra.endpoint}</p>` : ''}
      </div>`;
    }
    msg.innerHTML = html;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    messages.push({ role: 'bot', text });
  }

  function addUserMessage(text) {
    const container = document.getElementById('kclawMessages');
    const msg = document.createElement('div');
    msg.className = 'kclaw-msg user';
    msg.textContent = text;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    messages.push({ role: 'user', text });
  }

  function showTyping() {
    const container = document.getElementById('kclawMessages');
    const typing = document.createElement('div');
    typing.className = 'kclaw-typing';
    typing.id = 'kclawTyping';
    typing.innerHTML = '<span></span><span></span><span></span>';
    container.appendChild(typing);
    container.scrollTop = container.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById('kclawTyping');
    if (el) el.remove();
  }

  function showSuggestions(items) {
    const container = document.getElementById('kclawSuggestions');
    container.innerHTML = '';
    items.forEach(text => {
      const btn = document.createElement('button');
      btn.className = 'kclaw-suggestion';
      btn.textContent = text;
      btn.addEventListener('click', () => {
        document.getElementById('kclawInput').value = text;
        sendMessage();
      });
      container.appendChild(btn);
    });
  }

  function clearSuggestions() {
    document.getElementById('kclawSuggestions').innerHTML = '';
  }

  async function sendMessage() {
    const input = document.getElementById('kclawInput');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    addUserMessage(text);
    clearSuggestions();
    showTyping();

    try {
      // Try chat endpoint first
      const chatRes = await fetch(`${CONFIG.apiUrl}/api/hermes/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const chatData = await chatRes.json();

      hideTyping();

      if (chatData.success) {
        if (chatData.type === 'faq') {
          addBotMessage(chatData.response, { tip: chatData.tip });
          showSuggestions(CONFIG.suggestions);
        } else if (chatData.type === 'enhancement') {
          const rec = chatData.recommendation || {};
          addBotMessage(chatData.response, {
            engine: rec.engine,
            style: rec.style,
            endpoint: rec.apiEndpoint,
          });
          // Show alternative suggestions
          const altSuggestions = (chatData.alternatives || []).map(a => `🔄 ${a.reason}`);
          showSuggestions(altSuggestions.length > 0 ? altSuggestions : CONFIG.suggestions);
        } else {
          addBotMessage(chatData.response);
          if (chatData.suggestions) {
            showSuggestions(chatData.suggestions);
          }
        }
      } else {
        addBotMessage('抱歉，處理出了點問題。再試一次？');
        showSuggestions(CONFIG.suggestions);
      }
    } catch (err) {
      hideTyping();
      // Offline mode - use local enhancement
      addBotMessage(offlineResponse(text));
      showSuggestions(CONFIG.suggestions);
    }
  }

  // Offline fallback responses
  function offlineResponse(text) {
    const lower = text.toLowerCase();
    if (lower.includes('音樂') || lower.includes('music')) {
      return '🎵 ToneForge 可以幫你做音樂！輸入風格和心情，幾分鐘就生成。目前支援 Lofi、Techno、Cyberpunk 等風格。';
    }
    if (lower.includes('影片') || lower.includes('mv') || lower.includes('video')) {
      return '🎬 WireVision 是我們的 AI MV 引擎！上傳音樂，自動生成節拍同步的影片。';
    }
    if (lower.includes('動畫') || lower.includes('animation')) {
      return '🖼️ FrameForge 可以讓你的圖片動起來！上傳一張靜態圖，AI 注入動態效果。';
    }
    if (lower.includes('價格') || lower.includes('price')) {
      return '💰 我們有三個方案：Free ($0)、Pro ($15/月)、Enterprise (客製)。先用免費版試試！';
    }
    return '我是 KClaw 🐯 目前處於離線模式。連上網路後我可以幫你分析需求、推薦引擎、優化提示詞！';
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createWidget);
  } else {
    createWidget();
  }
})();
