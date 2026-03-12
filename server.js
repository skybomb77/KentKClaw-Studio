const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const WebSocket = require('ws');
const http = require('http');

const app = express();
const port = 3000;

const COMFY_SERVER = '192.168.50.124:8188';

app.use(express.static('public'));
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

// 存放每個任務的進度更新機制 (SSE)
const clients = new Map();

app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'public/mv-creator.html')));

// SSE 連線，讓前端可以即時收到算圖進度
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

app.post('/api/generate-mv', upload.single('audio'), async (req, res) => {
    try {
        const file = req.file;
        const promptText = req.body.prompt;
        const jobId = `job_${Date.now()}`;
        const clientId = `app_client_${Date.now()}`;
        
        // 1. 先回傳 OK，讓前端開始準備接收 SSE
        res.json({ success: true, jobId });
        
        console.log(`[Chaobang] 新任務 ${jobId}: ${promptText}`);

        // 2. 準備 ComfyUI 的 JSON
        const workflowPath = path.join(__dirname, '../ComfyUI/workflow_animatediff.json');
        let promptJson = null;
        if (fs.existsSync(workflowPath)) {
            promptJson = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
            if (promptJson["6"] && promptJson["6"]["inputs"]) {
                promptJson["6"]["inputs"]["text"] = promptText;
            }
        } else {
            console.error("找不到工作流 JSON！");
            sendToClient(jobId, { type: 'error', msg: '找不到 ComfyUI 工作流設定檔' });
            return;
        }

        // 3. 連線 ComfyUI WebSocket 以獲取進度
        const ws = new WebSocket(`ws://${COMFY_SERVER}/ws?clientId=${clientId}`);
        
        ws.on('open', () => {
            sendToClient(jobId, { type: 'log', msg: '📡 成功連上算圖伺服器，開始執行任務...' });
            
            // 呼叫 API 送出任務
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
                            videoUrl = `http://${COMFY_SERVER}/view?filename=${outputs[id].gifs[0].filename}`;
                            break;
                        }
                    }
                    if (videoUrl) {
                        sendToClient(jobId, { type: 'done', url: videoUrl });
                    } else {
                        sendToClient(jobId, { type: 'error', msg: '找不到生成的影片檔案' });
                    }
                } catch (e) {
                    sendToClient(jobId, { type: 'error', msg: '影片網址解析失敗' });
                }
                ws.close();
            }
        });
        
        ws.on('error', (err) => {
            console.error('WebSocket Error:', err);
            sendToClient(jobId, { type: 'error', msg: '算圖伺服器連線中斷' });
        });

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: '伺服器錯誤' });
    }
});

app.listen(port, () => {
    console.log(`🚀 [Chaobang AI MV] 後端就緒: http://localhost:${port}`);
});
