const express = require('express');
const cors = require('cors');
const http = require('http');

const app = express();
const PORT = process.env.MIDDLEWARE_PORT || 3000;
const HERMES_URL = process.env.HERMES_URL || 'http://127.0.0.1:3001';

// CORS
app.use(cors({ origin: true, methods: ['GET', 'POST', 'OPTIONS'], allowedHeaders: ['Content-Type', 'Authorization'] }));
app.use((req, res, next) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    if (req.method === 'OPTIONS') return res.status(204).end();
    next();
});
app.use(express.json());

// Proxy helper
function proxyToHermes(req, res, targetPath) {
    const url = new URL(targetPath, HERMES_URL);
    const options = {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname + (url.search || ''),
        method: req.method,
        headers: { 'Content-Type': 'application/json' }
    };

    const proxyReq = http.request(options, (proxyRes) => {
        let data = '';
        proxyRes.on('data', chunk => data += chunk);
        proxyRes.on('end', () => {
            res.status(proxyRes.statusCode).set(proxyRes.headers).send(data);
        });
    });

    proxyReq.on('error', (err) => {
        console.error(`[Middleware] Hermes unreachable: ${err.message}`);
        res.status(502).json({ success: false, error: 'Hermes API 服務無法連線' });
    });

    if (req.body && Object.keys(req.body).length > 0) {
        proxyReq.write(JSON.stringify(req.body));
    }
    proxyReq.end();
}

// ===== ROUTES =====

// Health check
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', service: 'middleware-proxy', hermes: HERMES_URL, timestamp: new Date().toISOString() });
});

// Smart routing → Hermes
app.post('/api/hermes/route', (req, res) => proxyToHermes(req, res, '/api/hermes/route'));
app.post('/api/hermes/enhance', (req, res) => proxyToHermes(req, res, '/api/hermes/enhance'));
app.post('/api/hermes/chat', (req, res) => proxyToHermes(req, res, '/api/hermes/chat'));

// Music generation → Hermes
app.post('/api/hermes/music/generate', (req, res) => proxyToHermes(req, res, '/api/hermes/music/generate'));
app.get('/api/hermes/music/styles', (req, res) => proxyToHermes(req, res, '/api/hermes/music/styles'));

// Generic proxy for any /api/hermes/* route
app.all('/api/hermes/*', (req, res) => proxyToHermes(req, res, req.path));

// Engine endpoints (App expects these)
app.post('/api/generate', (req, res) => proxyToHermes(req, res, '/api/hermes/route'));
app.post('/api/forge-music', (req, res) => proxyToHermes(req, res, '/api/hermes/music/generate'));

// Placeholder for video/image engines (need GPU engine running)
app.post('/api/generate-mv', (req, res) => {
    res.status(503).json({
        success: false,
        error: 'WireVision 影片引擎正在建置中',
        message: 'RTX 5070 Ti GPU 引擎即將上線',
        fallback: '/api/hermes/route'
    });
});

app.post('/api/generate-img2vid', (req, res) => {
    res.status(503).json({
        success: false,
        error: 'FrameForge 動畫引擎正在建置中',
        message: 'RTX 5070 Ti GPU 引擎即將上線',
        fallback: '/api/hermes/route'
    });
});

// LTXV Local Video Generation (text-to-video via ComfyUI)
const COMFYUI_URL = 'http://127.0.0.1:8188';
app.post('/api/generate-ltxv', async (req, res) => {
    try {
        const { prompt, negative, width = 768, height = 512, length = 49, steps = 40, cfg = 4.0, seed = 0 } = req.body;
        if (!prompt) return res.status(400).json({ success: false, error: 'Prompt is required' });

        const finalSeed = seed > 0 ? seed : Math.floor(Math.random() * 2147483647);
        const comfyPrompt = {
            "1": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "ltx-video-2b-v0.9.safetensors" } },
            "2": { "class_type": "CLIPLoader", "inputs": { "clip_name": "t5xxl_fp16.safetensors", "type": "ltxv" } },
            "3": { "class_type": "CLIPTextEncode", "inputs": { "text": prompt, "clip": ["2", 0] } },
            "4": { "class_type": "CLIPTextEncode", "inputs": { "text": negative || "low quality, blurry, distorted, watermark, ugly", "clip": ["2", 0] } },
            "5": { "class_type": "LTXVConditioning", "inputs": { "positive": ["3", 0], "negative": ["4", 0], "frame_rate": 24.0 } },
            "6": { "class_type": "EmptyLTXVLatentVideo", "inputs": { "width": parseInt(width), "height": parseInt(height), "length": parseInt(length), "batch_size": 1 } },
            "7": { "class_type": "KSampler", "inputs": { "model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1], "latent_image": ["6", 0], "seed": finalSeed, "steps": parseInt(steps), "cfg": parseFloat(cfg), "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0 } },
            "8": { "class_type": "VAEDecode", "inputs": { "samples": ["7", 0], "vae": ["1", 2] } },
            "9": { "class_type": "CreateVideo", "inputs": { "images": ["8", 0], "fps": 24.0 } },
            "10": { "class_type": "SaveVideo", "inputs": { "video": ["9", 0], "filename_prefix": `ltxv_${Date.now()}`, "format": "mp4", "codec": "h264" } }
        };

        const resp = await fetch(`${COMFYUI_URL}/prompt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: comfyPrompt })
        });
        const data = await resp.json();
        if (data.error) return res.status(400).json({ success: false, error: data.error });
        res.json({ success: true, prompt_id: data.prompt_id, seed: finalSeed });
    } catch (err) {
        res.status(500).json({ success: false, error: err.message });
    }
});

// Check LTXV generation status
app.get('/api/ltxv-status/:prompt_id', async (req, res) => {
    try {
        const resp = await fetch(`${COMFYUI_URL}/history`);
        const history = await resp.json();
        const info = history[req.params.prompt_id];
        if (!info) return res.json({ status: 'pending' });
        const status = info.status?.status_str || 'unknown';
        if (status === 'success') {
            const outputs = info.outputs || {};
            for (const nodeId of Object.keys(outputs)) {
                if (outputs[nodeId].videos) {
                    return res.json({ status: 'success', video: outputs[nodeId].videos[0] });
                }
            }
        }
        if (status === 'error') {
            const errMsg = info.status?.messages?.find(m => m[1]?.exception_message)?.[1]?.exception_message || 'Unknown error';
            return res.json({ status: 'error', error: errMsg });
        }
        res.json({ status });
    } catch (err) {
        res.json({ status: 'error', error: err.message });
    }
});

// 404
app.use((req, res) => {
    res.status(404).json({ success: false, error: 'Not found', path: req.path });
});

// Start
app.listen(PORT, () => {
    console.log(`\n⚡ Middleware Proxy v1.0 | Port ${PORT}`);
    console.log(`   Hermes: ${HERMES_URL}`);
    console.log(`   Health: /api/health`);
    console.log(`   Routes: /api/hermes/* → ${HERMES_URL}/api/hermes/*\n`);
});
