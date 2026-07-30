"""Food ViT #2: nateraw/vit-base-food101 + skylord/swin-finetuned-food101"""
import requests, os, warnings, json, time
warnings.filterwarnings('ignore')

models = [
    "nateraw/vit-base-food101",
    "skylord/swin-finetuned-food101",
]

for model_id in models:
    print(f"\n{'='*50}")
    print(f"Downloading: {model_id}")
    save_dir = f"backend/models/{model_id.split('/')[-1]}"
    os.makedirs(save_dir, exist_ok=True)

    for attempt in range(1, 8):
        try:
            api = f"https://huggingface.co/api/models/{model_id}"
            r = requests.get(api, verify=False, timeout=30)
            if r.status_code == 200:
                data = r.json()
                files = [s['rfilename'] for s in data.get('siblings', [])
                         if not s['rfilename'].startswith('.')]
                weights = [f for f in files if f.endswith('.bin') or f.endswith('.safetensors')]
                priority = weights + [f for f in files if f not in weights]

                base = f"https://huggingface.co/{model_id}/resolve/main"
                for fname in priority[:5]:  # 只要核心文件
                    url = f"{base}/{fname}"
                    dst = f"{save_dir}/{fname}"
                    if os.path.exists(dst):
                        print(f"  SKIP: {fname}")
                        continue
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    r = requests.get(url, verify=False, timeout=300)
                    with open(dst, 'wb') as f:
                        f.write(r.content)
                    print(f"  DONE: {fname} ({len(r.content)/1e6:.1f}MB)")
                print(f"{model_id} COMPLETE")
                break
            else:
                print(f"  HTTP {r.status_code} — skipping")
                break
        except Exception as e:
            print(f"  Attempt {attempt} failed: {str(e)[:80]}")
            time.sleep(min(attempt * 5, 30))

print("\nALL DONE")
