import json
import urllib.request

prompt = {
    "1": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "ltx-video-2b-v0.9.safetensors"
        }
    },
    "2": {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": "t5xxl_fp16.safetensors",
            "type": "ltxv"
        }
    },
    "3": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "A golden sunset over calm ocean waves, cinematic warm lighting, smooth camera pan, reflections on water, 4k quality",
            "clip": ["2", 0]
        }
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "low quality, worst quality, deformed, distorted, disfigured, motion smear, motion artifacts, bad anatomy, ugly",
            "clip": ["2", 0]
        }
    },
    "5": {
        "class_type": "LTXVConditioning",
        "inputs": {
            "positive": ["3", 0],
            "negative": ["4", 0],
            "frame_rate": 24.0
        }
    },
    "6": {
        "class_type": "EmptyLTXVLatentVideo",
        "inputs": {
            "width": 768,
            "height": 512,
            "length": 65,
            "batch_size": 1
        }
    },
    "7": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["5", 0],
            "negative": ["5", 1],
            "latent_image": ["6", 0],
            "seed": 42,
            "steps": 30,
            "cfg": 3.5,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["7", 0],
            "vae": ["1", 2]
        }
    },
    "9": {
        "class_type": "CreateVideo",
        "inputs": {
            "images": ["8", 0],
            "fps": 24.0
        }
    },
    "10": {
        "class_type": "SaveVideo",
        "inputs": {
            "video": ["9", 0],
            "filename_prefix": "ltxv_sunset_test",
            "format": "mp4",
            "codec": "h264"
        }
    }
}

payload = {"prompt": prompt}
req = urllib.request.Request(
    "http://127.0.0.1:8188/prompt",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)

try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(f"Queued! Prompt ID: {result.get('prompt_id')}")
    print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print(f"Error {e.code}: {error_body}")
except Exception as e:
    print(f"Error: {e}")
