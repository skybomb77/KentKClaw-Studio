# 🐯 Hermes API Server v1.0.0

Kent & KClaw Studio 智慧 AI 助手層

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/hermes/enhance | 智慧提示詞增強 |
| POST | /api/hermes/chat | 對話式 AI 助手 |
| POST | /api/hermes/route | 智慧引擎路由 |
| POST | /api/hermes/music/generate | 音樂生成 |
| GET | /api/hermes/engines | 引擎列表 |
| GET | /api/hermes/music/styles | 音樂風格 |
| GET | /api/hermes/health | 健康檢查 |

## 啟動

```bash
cd hermes-api-server && node server.js
# 或透過 start_app.js 自動啟動 (Port 3001)
```
