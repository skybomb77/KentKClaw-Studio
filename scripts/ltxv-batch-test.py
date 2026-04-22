import json
import urllib.request
import sys

tests = [
    {
        "name": "cyberpunk_rain",
        "prompt": "Rain-soaked cyberpunk alley at night, neon signs reflecting in puddles, steam rising from vents, a lone figure walking, cinematic moody lighting, blade runner style",
        "negative": "low quality, blurry, distorted, watermark, static, ugly, deformed",
        "width": 768, "height": 512, "length": 65,
        "steps": 40, "cfg": 4.0, "seed": 400
    },
    {
        "name": "ocean_waves",
        "prompt": "Crashing ocean waves in slow motion, golden sunset light, water droplets suspended in air, dramatic cinematic shot, deep blue and orange colors",
        "negative": "low quality, blurry, distorted, watermark, static, ugly",
        "width": 768, "height": 512, "length": 65,
        "steps": 40, "cfg": 4.0, "seed": 500
    },
    {
        "name": "anime_samurai",
        "prompt": "An anime samurai standing on a cliff overlooking a vast landscape, cherry blossoms blowing in wind, dramatic clouds, golden hour, makoto shinkai style",
        "negative": "low quality, blurry, distorted, watermark, ugly, deformed face, bad anatomy",
        "width": 512, "height": 768, "length": 65,
        "steps": 40, "cfg": 4.0, "seed": 600
    },
    {
        "name": "cozy_cafe",
        "prompt": "Cozy coffee shop interior, warm amber lighting, steam rising from cup, rain on window, soft jazz atmosphere, shallow depth of field, cinematic",
        "negative": "low quality, blurry, distorted, watermark, static, ugly, overexposed",
        "width": 768, "height": 512, "length": 49,
        "steps": 40, "cfg": 4.0, "seed": 700
    },
    {
        "name": "fantasy_castle",
        "prompt": "Fantasy castle floating in clouds, waterfalls cascading down, magical glowing crystals, epic wide shot, lord of the rings style, dramatic lighting",
        "negative": "low quality, blurry, distorted, watermark, static, ugly, lowres",
        "width": 768, "height": 512, "length": 65,
        "steps": 45, "cfg": 4.5, "seed": 800
    }
]

idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
t = tests[idx]
print(f"Test: {t['name']} | {t['width']}x{t['height']} | {t['length']}f | {t['steps']}steps | cfg={t['cfg']}")

prompt = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "ltx-video-2b-v0.9.safetensors"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "t5xxl_fp16.safetensors", "type": "ltxv"}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": t["prompt"], "clip": ["2", 0]}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": t["negative"], "clip": ["2", 0]}},
    "5": {"class_type": "LTXVConditioning", "inputs": {"positive": ["3", 0], "negative": ["4", 0], "frame_rate": 24.0}},
    "6": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": t["width"], "height": t["height"], "length": t["length"], "batch_size": 1}},
    "7": {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1], "latent_image": ["6", 0],
        "seed": t["seed"], "steps": t["steps"], "cfg": t["cfg"],
        "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0
    }},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
    "9": {"class_type": "CreateVideo", "inputs": {"images": ["8", 0], "fps": 24.0}},
    "10": {"class_type": "SaveVideo", "inputs": {"video": ["9", 0], "filename_prefix": f"ltxv_{t['name']}", "format": "mp4", "codec": "h264"}}
}

payload = {"prompt": prompt}
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(f"Queued! Prompt ID: {result.get('prompt_id')}")
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
