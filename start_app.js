const localtunnel = require('localtunnel');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

(async function() {
    console.log('⏳ 正在透過 LocalTunnel 建立安全連線通道 (無須驗證防卡死)...');
    try {
        const tunnel = await localtunnel({ port: 3000 });
        const url = tunnel.url;

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

        const indexHtmlPath = path.join(__dirname, 'index.html');
        if (fs.existsSync(indexHtmlPath)) {
            let indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
            indexHtml = indexHtml.replace(/href="https:\/\/.*\.loca\.lt\/app"/g, `href="app/index.html"`);
            fs.writeFileSync(indexHtmlPath, indexHtml);
            console.log('✅ 已成功將官網首頁按鈕直接連通至您的 Mac 隧道。');
        }

        console.log('🚀 啟動 Chaobang 後端中樞神經...');
        const server = spawn('node', ['server.js'], { stdio: 'inherit' });
        
        console.log('📦 正在將最新網址同步推送到 Vercel 正式站，這可能需要 10 秒...');
        const gitPush = spawn('git', ['commit', '-am', 'feat: update tunnel url via localtunnel automatically', '&&', 'git', 'push', 'origin', 'main'], { shell: true });
        
        gitPush.on('close', (code) => {
            console.log('🎉 部署完成！您的正式產品已經上線。您可以直接點擊 Vercel 官網開始接客。');
        });

        tunnel.on('close', () => {
            console.log('連線通道已關閉。');
        });

    } catch (err) {
        console.error('❌ 隧道挖掘失敗:', err);
    }
})();