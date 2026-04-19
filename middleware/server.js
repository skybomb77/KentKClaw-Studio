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
