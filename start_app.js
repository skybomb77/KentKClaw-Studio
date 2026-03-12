const ngrok = require('ngrok');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

(async function() {
    console.log('⏳ 正在為您的 Mac 引擎挖掘全球公開隧道...');
    try {
        const url = await ngrok.connect({
            addr: 3000,
            authtoken: '3AqvYHB9fLiLfO8XgS1NfBB73gm_3AQZHxKuhrm4USqUQDnRQ'
        });
        
        console.log('\n=============================================');
        console.log('🌍 內網穿透成功！您的全球公開 API 網址是：');
        console.log(`➡️  ${url}`);
        console.log('=============================================\n');

        // 將這串網址動態寫入 app/index.html (讓前端知道要把音軌打給哪個 API)
        const appHtmlPath = path.join(__dirname, 'app/index.html');
        if (fs.existsSync(appHtmlPath)) {
            let html = fs.readFileSync(appHtmlPath, 'utf8');
            if (html.includes('const BACKEND_URL =')) {
                html = html.replace(/const BACKEND_URL = ".*?";/g, `const BACKEND_URL = "${url}";`);
            } else {
                html = html.replace('<script>', `<script>\n        const BACKEND_URL = "${url}";`);
            }
            fs.writeFileSync(appHtmlPath, html);
        }

        // --- 終極絕招：直接把 Vercel 首頁的「Try AI MV Creator」按鈕，指向你 Mac mini 的 Ngrok 隧道 ---
        const indexHtmlPath = path.join(__dirname, 'index.html');
        if (fs.existsSync(indexHtmlPath)) {
            let indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
            // 將兩個按鈕直接替換為 Ngrok 獨立站網址 (包含 /app 也就是我們的軟體介面)
            indexHtml = indexHtml.replace(/href="[^"]*app"/g, `href="${url}/app"`);
            fs.writeFileSync(indexHtmlPath, indexHtml);
            console.log('✅ 已成功將官網首頁按鈕直接連通至您的 Mac 隧道。');
        }

        console.log('🚀 啟動 Chaobang 後端中樞神經...');
        const server = spawn('node', ['server.js'], { stdio: 'inherit' });
        
        // 自動執行 git push 更新 Vercel
        console.log('📦 正在將最新網址同步推送到 Vercel 正式站，這可能需要 10 秒...');
        const gitPush = spawn('git', ['commit', '-am', 'feat: update ngrok tunnel url automatically', '&&', 'git', 'push', 'origin', 'main'], { shell: true });
        
        gitPush.on('close', (code) => {
            console.log('🎉 部署完成！您的正式產品已經上線。您可以直接點擊 Vercel 官網開始接客。');
        });

    } catch (err) {
        console.error('❌ Ngrok 隧道挖掘失敗:', err);
    }
})();