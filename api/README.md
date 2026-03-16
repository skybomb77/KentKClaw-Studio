# ToneForge API

## Start

```bash
cd api
npm install
cp .env.example .env
npm run dev
```

## Endpoints

- `GET /health`
- `POST /generate`

## POST /generate body

```json
{
  "prompt": "glossy fashion-tech beat",
  "useCase": "Short video",
  "duration": "15s"
}
```

## Behavior

- If `STABLE_AUDIO_API_KEY` is present, the server tries the Stable Audio-style provider endpoint.
- If the key is missing or the provider fails, the server falls back to mock tracks.

## Env

- `TONEFORGE_PROVIDER=stable-audio`
- `STABLE_AUDIO_API_KEY=...`
- `STABLE_AUDIO_API_BASE=https://api.stability.ai`
- `STABLE_AUDIO_GENERATE_PATH=/v2beta/audio/stable-audio/generate`
- `MAX_DURATION_SECONDS=60`

## Notes

The provider path/base are configurable on purpose. If the official endpoint differs, update `.env` without changing app code.
