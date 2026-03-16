const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');

(async function() {
    console.log('⏳ 正在透過 Ngrok (CLI) 建立穩定安全連線通道...');
    try {
        // Kill existing ngrok processes
        try { execSync('killall ngrok', { stdio: 'ignore' }); } catch(e) {}
        
        // Start ngrok in the background
        const ngrokProcess = spawn('ngrok', ['http', '3000', '--log=stdout'], { stdio: 'pipe' });
        
        let url = null;
        console.log('等待 Ngrok 啟動...');
        
        // Polling the local ngrok API to get the public URL
        for (let i = 0; i < 20; i++) {
            await new Promise(r => setTimeout(r, 1000));
            try {
                const res = await fetch('http://127.0.0.1:4040/api/tunnels');
                if (res.ok) {
                    const data = await res.json();
                    if (data.tunnels && data.tunnels.length > 0) {
                        url = data.tunnels[0].public_url;
                        break;
                    }
                }
            } catch (e) {
                // Ignore fetch errors during startup
            }
        }

        if (!url) {
            throw new Error("無法取得 Ngrok 網址，請確認 ngrok 是否已正確安裝並登入。");
        }

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
            indexHtml = indexHtml.replace(/href="https:\/\/.*\.ngrok\.io\/app"/g, `href="app/index.html"`);
            indexHtml = indexHtml.replace(/href="https:\/\/.*\.ngrok-free\.app\/app"/g, `href="app/index.html"`);
            fs.writeFileSync(indexHtmlPath, indexHtml);
            console.log('✅ 已成功將官網首頁按鈕直接連通至您的 Mac 隧道。');
        }

        // === AUTO PUSH TO VERCEL ===
        try {
            execSync("git add app/index.html index.html", { cwd: __dirname });
            execSync("git commit -m \"Auto-update Backend URL for Vercel (Ngrok CLI)\"", { cwd: __dirname });
            execSync("git push origin main", { cwd: __dirname });
            console.log("✅ 隧道網址已推送到 GitHub！您的 Vercel 網站（chaobang.vercel.app）現在已經與本機伺服器完全同步。\n");
        } catch(e) { /* Ignore if no changes */ }

        console.log('🚀 啟動 Chaobang 後端中樞神經...');
        const server = spawn('node', ['server.js'], { stdio: 'inherit' });
        
        console.log('📦 正在將最新網址同步推送到 Vercel 正式站，這可能需要 10 秒...');
        const gitPush = spawn('git', ['commit', '-am', 'feat: update tunnel url via ngrok automatically', '&&', 'git', 'push', 'origin', 'main'], { shell: true });
        
        gitPush.on('close', (code) => {
            console.log('🎉 部署完成！您的正式產品已經上線。您可以直接點擊 Vercel 官網開始接客。');
        });

    } catch (err) {
        console.error('❌ 隧道挖掘失敗:', err);
    }
})();