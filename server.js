const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const WebSocket = require('ws');
const http = require('http');
const cors = require('cors');

const { spawn } = require('child_process');

const app = express();
const port = 3000;
const COMFY_SERVER = '127.0.0.1:8188';

// 啟用 CORS 允許來自 GitHub Pages 和 Vercel 的請求
app.use(cors({
    origin: true, // 全部放行
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'ngrok-skip-browser-warning', 'bypass-tunnel-reminder'],
    credentials: true,
    preflightContinue: false,
    optionsSuccessStatus: 204
}));

// 中間件：確保所有回應都帶有必要的 Header，並且解決 Ngrok 403
app.use((req, res, next) => {
    const origin = req.headers.origin || '*';
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, ngrok-skip-browser-warning, bypass-tunnel-reminder, x-clerk-auth-token');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('ngrok-skip-browser-warning', 'true');

    // 驗證 Clerk Token (選填，目前先 Log 出來)
    if (req.headers.authorization) {
        console.log(`[Auth] Received Token from: ${req.headers.origin}`);
    }

    // 關鍵：如果瀏覽器發送 OPTIONS 預檢請求，直接回傳 200/204
    if (req.method === 'OPTIONS') {
        return res.status(204).end();
    }
    next();
});

app.use(express.static(__dirname));
app.use('/favicon.ico', (req, res) => res.status(204).end());
app.use('/app', express.static(path.join(__dirname, 'app')));
app.use(express.json());

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadPath = path.join(__dirname, 'audio_output');
    if (!fs.existsSync(uploadPath)) fs.mkdirSync(uploadPath);
    cb(null, uploadPath);
  },
  filename: (req, file, cb) => {
    cb(null, `upload_${Date.now()}_${file.originalname}`);
  }
});
const upload = multer({ storage: storage });

const clients = new Map();

// 確保 /app 路由精準指向我們的前端介面
app.get('/app', (req, res) => res.sendFile(path.join(__dirname, 'app', 'index.html')));

// 建立一個標準的 HTTP 伺服器
const server = http.createServer(app);

app.get('/health', (req, res) => res.json({ status: 'ok', engine: COMFY_SERVER }));

// 初始化 WebSocket 伺服器 (供前端監聽算圖進度)
const wss = new WebSocket.Server({ noServer: true });

server.on('upgrade', (request, socket, head) => {
    const pathname = request.url;
    console.log(`[Upgrade] Request to: ${pathname}`);
    if (pathname.includes('/api/ws/')) {
        wss.handleUpgrade(request, socket, head, (ws) => {
            wss.emit('connection', ws, request);
        });
    } else {
        console.log(`[Upgrade] Rejected: ${pathname}`);
        socket.destroy();
    }
});

wss.on('connection', (ws, request) => {
    const jobId = request.url.split('/').pop();
    clients.set(jobId, ws);
    console.log(`[WebSocket] 客戶端已連線至任務: ${jobId}`);
    
    ws.on('close', () => {
        clients.delete(jobId);
        console.log(`[WebSocket] 任務連線已斷開: ${jobId}`);
    });
});

function sendToClient(jobId, data) {
    const ws = clients.get(jobId);
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

// 移除舊的 SSE 路由
// app.get('/api/stream/:jobId', ...); 

app.get('/api/video/:filename', (req, res) => {
    const filename = req.params.filename;
    // 支援 ComfyUI 預設的 view API
    const url = `http://${COMFY_SERVER}/view?filename=${filename}&type=output`;
    http.get(url, (response) => {
            if (response.statusCode !== 200) {
                res.status(response.statusCode).send('Error fetching video from engine');
                return;
            }
        res.setHeader('Content-Type', 'video/mp4');
        response.pipe(res);
    }).on('error', (err) => {
        res.status(500).send('Error fetching video from engine');
    });
});

// === ToneForge: AI 音樂鍛造 API ===
app.post('/api/forge-music', async (req, res) => {
    const { style, mood, duration } = req.body;
    const outputFilename = `forge_${Date.now()}.wav`;
    const outputPath = path.join(__dirname, 'audio_output', outputFilename);
    
    console.log(`[ToneForge] 鍛造請求: ${style} | ${mood} | ${duration}s`);

    try {
        // 這裡調用 Python 腳本進行物理建模合成或 AI 生成
        const scriptPath = path.join(__dirname, 'scripts/generate_music.py');
        
        if (!fs.existsSync(scriptPath)) {
            return res.status(404).json({ success: false, error: 'Synthesis script not found' });
        }

        const pythonProcess = spawn('python', [
            scriptPath,
            '--style', style || 'Lofi Hip Hop',
            '--duration', duration || 15,
            '--output', outputPath
        ]);

        let errorOutput = '';
        pythonProcess.stderr.on('data', (data) => {
            errorOutput += data.toString();
        });

        pythonProcess.on('error', (err) => {
            console.error('[ToneForge] Failed to start python process:', err);
            if (!res.headersSent) res.status(500).json({ success: false, error: 'Failed to start engine' });
        });

        pythonProcess.on('close', (code) => {
            if (code === 0) {
                // 回傳完整網址，包含通訊協定與主機名
                const audioUrl = `${req.protocol}://${req.get('host')}/audio_output/${outputFilename}`;
                console.log(`[ToneForge] 鍛造成功: ${audioUrl}`);
                res.json({ success: true, audioUrl });
            } else {
                console.error(`[ToneForge] Python exited with code ${code}: ${errorOutput}`);
                if (!res.headersSent) res.status(500).json({ success: false, error: `Synthesis failed (Code ${code})` });
            }
        });
    } catch (err) {
        console.error('[ToneForge] Unexpected Error:', err);
        if (!res.headersSent) res.status(500).json({ success: false, error: err.message });
    }
});

// 靜態資源：允許訪問產出的音訊檔
app.use('/audio_output', express.static(path.join(__dirname, 'audio_output')));

app.post('/api/generate-mv', upload.single('audio'), async (req, res) => {
    try {
        const file = req.file;
        const promptText = req.body.prompt;
        const lyrics = req.body.lyrics; // 新增：抓取歌詞欄位
        const ratio = req.body.ratio || '16:9';
        const resolution = req.body.resolution || '720p';
        const jobId = `job_${Date.now()}`;
        const clientId = `app_client_${Date.now()}`;
        
        if (file) {
            const comfyInputPath = path.join(__dirname, '../ComfyUI/input', file.filename);
            if (!fs.existsSync(path.dirname(comfyInputPath))) {
                fs.mkdirSync(path.dirname(comfyInputPath), { recursive: true });
            }
            fs.copyFileSync(file.path, comfyInputPath);
            console.log(`[隧道測試] 已收到客戶端音軌並存入引擎: ${file.filename}`);
        }

        res.json({ success: true, jobId });
        console.log(`[Chaobang SaaS] 新客戶任務 ${jobId} | 比例: ${ratio} | 畫質: ${resolution} | 提示詞: ${promptText}`);

        const workflowPath = path.join(__dirname, '../ComfyUI/workflow_animatediff.json');
        if (!fs.existsSync(workflowPath)) {
            console.error('Workflow 檔案不存在:', workflowPath);
            return res.status(500).json({ success: false, error: "System Configuration Error (Workflow Missing)" });
        }
        let promptJson = null;
        if (fs.existsSync(workflowPath)) {
            promptJson = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
            
            if (promptJson["11"] && promptJson["11"]["inputs"]) {
                // 哥，調優 15 秒 (120 幀)，確保 5070 Ti 滿速運轉
                promptJson["11"]["inputs"]["batch_size"] = 120; 
            }

            // --- 音訊自動掛載 (修復沒聲音問題) ---
            if (file) {
                promptJson["20"] = {
                    "inputs": { "audio": file.filename },
                    "class_type": "VHS_AudioLoader",
                    "_meta": { "title": "Audio Engine" }
                };
                if (promptJson["12"] && promptJson["12"]["inputs"]) {
                    promptJson["12"]["inputs"]["audio"] = ["20", 0];
                }
            }

            // 優化滑動窗口參數，讓引擎更早開始輸出第一幀
            promptJson["15"] = {
                "inputs": {
                    "context_length": 16,
                    "context_stride": 1,
                    "context_overlap": 4,
                    "context_schedule": "uniform",
                    "closed_loop": false,
                    "fuse_method": "flat",
                    "use_on_equal_length": false,
                    "start_percent": 0,
                    "guarantee_steps": 1
                },
                "class_type": "ADE_AnimateDiffUniformContextOptions",
                "_meta": { "title": "顯存優化核心" }
            };

            // 將優化機制掛載到 AnimateDiff 載入器 (Node 10)
            if (promptJson["10"] && promptJson["10"]["inputs"]) {
                promptJson["10"]["inputs"]["context_options"] = ["15", 0];
            }

            // 確保輸出幀率與長度匹配 (Node 12)
            if (promptJson["12"] && promptJson["12"]["inputs"]) {
                promptJson["12"]["inputs"]["frame_rate"] = 8; 
            }

            // 調回更輕量化的算圖參數，確保引擎「秒給回應」
            if (promptJson["3"] && promptJson["3"]["inputs"]) {
                promptJson["3"]["inputs"]["seed"] = Math.floor(Math.random() * 1000000); 
                promptJson["3"]["inputs"]["steps"] = 6; // Blackwell 加速：6 步即可，省下一半時間
                promptJson["3"]["inputs"]["cfg"] = 2.5; 
            }
            
            // 核心邏輯：將提示詞與歌詞完全分開處理，使用不同的算圖節點
            
            // 節點 6 保持為視覺風格提示詞
            if (promptJson["6"] && promptJson["6"]["inputs"]) {
                promptJson["6"]["inputs"]["text"] = promptText || "masterpiece, best quality, highly detailed, neon cyberpunk";
            }

            // 新增節點 13：專門處理歌詞/意象
            promptJson["13"] = {
                "inputs": {
                    "text": lyrics || "",
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": { "title": "Lyrics Processor" }
            };

            // 新增節點 14：將風格(6)與歌詞(13)合併
            promptJson["14"] = {
                "inputs": {
                    "conditioning_1": ["6", 0],
                    "conditioning_2": ["13", 0]
                },
                "class_type": "ConditioningCombine",
                "_meta": { "title": "Merge Visuals & Lyrics" }
            };

            // 讓算圖器(3)改從合併後的節點(14)接收正面條件
            if (promptJson["3"] && promptJson["3"]["inputs"]) {
                promptJson["3"]["inputs"]["positive"] = ["14", 0];
            }

            // --- 自動計算尺寸比例 (Aspect Ratio) ---
            if (promptJson["11"] && promptJson["11"]["inputs"]) {
                let baseW = 910, baseH = 512;
                if (ratio === '9:16') { baseW = 512; baseH = 910; }
                else if (ratio === '1:1') { baseW = 512; baseH = 512; }
                
                // 如果是 1080p (Pro)，將長寬放大 1.5 倍 (考量 Mac mini 記憶體極限)
                if (resolution === '1080p') {
                    baseW = Math.floor(baseW * 1.5);
                    baseH = Math.floor(baseH * 1.5);
                    // 確保是 8 的倍數 (ComfyUI 限制)
                    baseW = baseW - (baseW % 8);
                    baseH = baseH - (baseH % 8);
                }
                
                promptJson["11"]["inputs"]["width"] = baseW;
                promptJson["11"]["inputs"]["height"] = baseH;
            }
        } else {
            console.error("找不到工作流 JSON！");
            sendToClient(jobId, { type: 'error', msg: '找不到 ComfyUI 工作流設定檔' });
            return;
        }

        const ws = new WebSocket(`ws://${COMFY_SERVER}/ws?clientId=${clientId}`);
        
        ws.on('open', () => {
            console.log(`[ComfyWS] 成功建立與算圖引擎的 WebSocket 連線`);
            sendToClient(jobId, { type: 'log', msg: '📡 成功穿透內網連接到算圖引擎，開始為您執行...' });
            const data = JSON.stringify({ prompt: promptJson, client_id: clientId });
            const reqComfy = http.request({
                hostname: COMFY_SERVER.split(':')[0],
                port: 8188,
                path: '/prompt',
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
            });
            reqComfy.on('error', (e) => {
                console.error(`[ComfyAPI] 請求錯誤: ${e.message}`);
                sendToClient(jobId, { type: 'error', msg: `引擎請求失敗: ${e.message}` });
            });
            reqComfy.write(data);
            reqComfy.end();
        });

        ws.on('message', (data) => {
            const message = JSON.parse(data);
            console.log(`[ComfyWS] 收到消息類型: ${message.type}`);
            if (message.type === 'progress') {
                const percent = Math.round((message.data.value / message.data.max) * 100);
                sendToClient(jobId, { type: 'progress', percent, val: message.data.value, max: message.data.max });
            }
            if (message.type === 'executed') {
                try {
                    const outputs = message.data.output;
                    let videoUrl = null;
                    
                    // 修正：ComfyUI WS 的 executed 訊息中，output 直接就是該節點的內容
                    if (outputs.gifs && outputs.gifs.length > 0) {
                        const filename = outputs.gifs[0].filename;
                        videoUrl = `${req.protocol}://${req.get('host')}/api/video/${filename}`;
                    } else if (outputs.images && outputs.images.length > 0) {
                        const filename = outputs.images[0].filename;
                        videoUrl = `${req.protocol}://${req.get('host')}/api/video/${filename}`;
                    }
                    
                    if (videoUrl) {
                        console.log(`[JobDone] ${jobId} -> ${videoUrl}`);
                        sendToClient(jobId, { type: 'done', url: videoUrl });
                    }
                } catch (e) {
                    console.error('影片網址解析失敗:', e);
                }
                // 注意：這裡不主動關閉，除非確定是最終節點，或者交給客戶端斷開
                // ws.close(); 
            }
        });
        
        ws.on('error', (err) => {
            sendToClient(jobId, { type: 'error', msg: '內部算圖引擎離線，請聯繫管理員啟動伺服器' });
        });

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: '伺服器錯誤' });
    }
});

// 改用 server.listen 取代 app.listen
server.listen(port, () => {
    console.log(`🚀 [Chaobang SaaS Node] 本機引擎就緒於 port ${port}`);
});