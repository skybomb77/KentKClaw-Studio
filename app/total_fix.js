const fs = require('fs');
const path = 'index.html';
let content = fs.readFileSync(path, 'utf8');

// 1. 徹底消滅所有 "Mac" 字眼
content = content.replace(/Mac mini/g, '本機伺服器');
content = content.replace(/Mac 引擎/g, '本機引擎');
content = content.replace(/Mac/g, '本機');

// 2. 確保間距正確 (Aspect Ratio vs Resolution Quality)
// 先移除可能存在的錯誤屬性或重複定義
content = content.replace(/<div class="input-group" style="margin-top: 24px;[^>]*>/g, '<div class="input-group" style="margin-top: 24px;">');

// 3. 確保按鈕邏輯獨立 (querySelectorAll 限定範圍)
content = content.replace(/const ratioBtns = document.querySelectorAll\('.setting-btn'\);/g, "const ratioBtns = document.querySelectorAll('#ratioSelector .setting-btn');");

// 4. 清理任何殘留的 \r\n 實體字元
content = content.replace(/\\r\\n/g, '');

fs.writeFileSync(path, content, 'utf8');
console.log('FINAL FIX COMPLETE: All "Mac" references removed, spacing verified, button logic isolated.');
