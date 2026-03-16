const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const WebSocket = require('ws');
const http = require('http');
const cors = require('cors');

const app = express();
const port = 3000;
const COMFY_SERVER = '127.0.0.1:8188';

// 啟用 CORS 允許來自 Vercel 和 Ngrok 隧道的請求
app.use(cors());
app.use(express.static(__dirname));
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

app.get('/api/stream/:jobId', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();
    clients.set(req.params.jobId, res);
    
    req.on('close', () => clients.delete(req.params.jobId));
});

function sendToClient(jobId, data) {
    const res = clients.get(jobId);
    if (res) res.write(`data: ${JSON.stringify(data)}\n\n`);
}

app.get('/api/video/:filename', (req, res) => {
    const filename = req.params.filename;
    const url = `http://${COMFY_SERVER}/view?filename=${filename}`;
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

app.post('/api/generate-mv', upload.single('audio'), async (req, res) => {
    try {
        const file = req.file;
        const promptText = req.body.prompt;
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
            console.error('Workflow 檔案不存在');
            return res.status(500).json({ success: false, error: "System Configuration Error (Workflow Missing)" });
        }
        let promptJson = null;
        if (fs.existsSync(workflowPath)) {
            promptJson = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
            if (promptJson["6"] && promptJson["6"]["inputs"]) {
                promptJson["6"]["inputs"]["text"] = promptText;
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
            sendToClient(jobId, { type: 'log', msg: '📡 成功穿透內網連接到算圖引擎，開始為您執行...' });
            const data = JSON.stringify({ prompt: promptJson, client_id: clientId });
            const reqComfy = http.request({
                hostname: COMFY_SERVER.split(':')[0],
                port: 8188,
                path: '/prompt',
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
            });
            reqComfy.write(data);
            reqComfy.end();
        });

        ws.on('message', (data) => {
            const message = JSON.parse(data);
            if (message.type === 'progress') {
                const percent = Math.round((message.data.value / message.data.max) * 100);
                sendToClient(jobId, { type: 'progress', percent, val: message.data.value, max: message.data.max });
            }
            if (message.type === 'executed') {
                try {
                    const outputs = message.data.output;
                    let videoUrl = null;
                    for (let id of Object.keys(outputs)) {
                        if (outputs[id] && outputs[id].gifs) {
                            const filename = outputs[id].gifs[0].filename;
                            videoUrl = `${req.protocol}://${req.get('host')}/api/video/${filename}`;
                            break;
                        }
                    }
                    if (videoUrl) sendToClient(jobId, { type: 'done', url: videoUrl });
                    else sendToClient(jobId, { type: 'error', msg: '找不到生成的影片檔案' });
                } catch (e) {
                    sendToClient(jobId, { type: 'error', msg: '影片網址解析失敗' });
                }
                ws.close();
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

app.listen(port, () => {
    console.log(`🚀 [Chaobang SaaS Node] 本機引擎就緒於 port ${port}`);
});