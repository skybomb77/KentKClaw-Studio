import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const port = process.env.PORT || 8787;
const provider = (process.env.TONEFORGE_PROVIDER || 'stable-audio').toLowerCase();
const apiKey = process.env.STABLE_AUDIO_API_KEY;
const apiBase = process.env.STABLE_AUDIO_API_BASE || 'https://api.stability.ai';
const generatePath = process.env.STABLE_AUDIO_GENERATE_PATH || '/v2beta/audio/stable-audio/generate';
const maxDurationSeconds = Number(process.env.MAX_DURATION_SECONDS || 60);

function durationToSeconds(duration) {
  const match = String(duration || '').match(/(\d+)/);
  return match ? Math.min(Number(match[1]), maxDurationSeconds) : 15;
}

function buildPrompt(prompt, useCase, duration) {
  return `${prompt}. Use case: ${useCase}. Duration: ${duration}. High quality, clean mix, production-ready.`;
}

function buildMockTracks(prompt, useCase, duration) {
  const titles = ['Pulse Cut', 'Velvet Rush', 'Chrome Drift'];
  return titles.map((title, i) => ({
    id: `mock-${i + 1}`,
    title,
    duration,
    useCase,
    bpm: [98, 112, 128][i],
    previewUrl: null,
    mood: prompt.split(' ').slice(0, 4).join(' '),
    source: 'mock'
  }));
}

async function stableAudioGenerate({ prompt, useCase, duration }) {
  if (!apiKey) {
    return { mode: 'mock', reason: 'missing_api_key', tracks: buildMockTracks(prompt, useCase, duration) };
  }

  const seconds = durationToSeconds(duration);
  const payload = {
    prompt: buildPrompt(prompt, useCase, duration),
    duration: seconds,
    output_format: 'mp3'
  };

  const response = await fetch(`${apiBase}${generatePath}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      Accept: 'application/json'
    },
    body: JSON.stringify(payload)
  });

  const contentType = response.headers.get('content-type') || '';
  if (!response.ok) {
    const errorBody = contentType.includes('application/json') ? await response.json().catch(() => ({})) : await response.text().catch(() => '');
    return {
      mode: 'mock',
      reason: 'provider_error',
      providerStatus: response.status,
      providerError: errorBody,
      tracks: buildMockTracks(prompt, useCase, duration)
    };
  }

  if (contentType.includes('application/json')) {
    const data = await response.json();
    const candidates = Array.isArray(data?.tracks) ? data.tracks : Array.isArray(data?.audio) ? data.audio : [];
    if (!candidates.length) {
      return { mode: 'mock', reason: 'empty_provider_response', tracks: buildMockTracks(prompt, useCase, duration) };
    }
    return {
      mode: 'live',
      provider: 'stable-audio',
      tracks: candidates.slice(0, 3).map((track, i) => ({
        id: track.id || `live-${i + 1}`,
        title: track.title || `ToneForge Track ${i + 1}`,
        duration,
        useCase,
        bpm: track.bpm || [100, 114, 128][i] || 120,
        previewUrl: track.url || track.preview_url || track.audio_url || null,
        mood: prompt.split(' ').slice(0, 4).join(' '),
        source: 'live'
      }))
    };
  }

  const arrayBuffer = await response.arrayBuffer();
  const base64Audio = Buffer.from(arrayBuffer).toString('base64');
  return {
    mode: 'live',
    provider: 'stable-audio',
    tracks: [{
      id: 'live-1',
      title: 'ToneForge Track 1',
      duration,
      useCase,
      bpm: 120,
      previewUrl: `data:audio/mpeg;base64,${base64Audio}`,
      mood: prompt.split(' ').slice(0, 4).join(' '),
      source: 'live'
    }]
  };
}

app.get('/health', (_req, res) => {
  res.json({
    ok: true,
    service: 'toneforge-api',
    provider,
    configured: Boolean(apiKey)
  });
});

app.post('/generate', async (req, res) => {
  const { prompt, useCase, duration } = req.body || {};
  if (!prompt || !useCase || !duration) {
    return res.status(400).json({ error: 'prompt, useCase, duration are required' });
  }

  try {
    const result = provider === 'stable-audio'
      ? await stableAudioGenerate({ prompt, useCase, duration })
      : { mode: 'mock', reason: 'unknown_provider', tracks: buildMockTracks(prompt, useCase, duration) };

    return res.json(result);
  } catch (error) {
    return res.status(200).json({
      mode: 'mock',
      reason: 'server_exception',
      error: error instanceof Error ? error.message : String(error),
      tracks: buildMockTracks(prompt, useCase, duration)
    });
  }
});

app.listen(port, () => {
  console.log(`ToneForge API running on http://localhost:${port}`);
});
