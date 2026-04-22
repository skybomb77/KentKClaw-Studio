import json
import urllib.request
import sys

tests = [
    {
        "name": "cinematic_city",
        "prompt": "A cinematic aerial shot of a futuristic city at night, neon lights reflecting on wet streets, rain falling, camera slowly descending, 4k movie quality",
        "negative": "low quality, blurry, distorted, watermark, static, ugly",
        "width": 768, "height": 512, "length": 49,
        "steps": 30, "cfg": 3.5, "seed": 100
    },
    {
        "name": "nature_forest",
        "prompt": "Sunlight streaming through a magical forest canopy, leaves gently swaying in the breeze, particles floating in golden light rays, peaceful nature",
        "negative": "low quality, blurry, distorted, watermark, static, ugly, deformed",
        "width": 768, "height": 512, "length": 65,
        "steps": 40, "cfg": 4.0, "seed": 200
    },
    {
        "name": "anime_character",
        "prompt": "An anime girl standing on a rooftop at sunset, wind blowing her hair, cityscape background, warm golden hour lighting, studio ghibli style",
        "negative": "low quality, blurry, distorted, watermark, ugly, deformed face, bad anatomy",
        "width": 512, "height": 768, "length": 49,
        "steps": 30, "cfg": 3.5, "seed": 300
    }
]

# Pick test from command line arg or run first
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
t = tests[idx]
print(f"Running test: {t['name']} ({t['width']}x{t['height']}, {t['length']}frames, {t['steps']}steps, cfg={t['cfg']})")

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
