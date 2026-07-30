"""Fruits 360 自动续传下载 — 断了就重连"""
import kagglehub, time
max_retries = 20
for i in range(1, max_retries + 1):
    print(f"\n{'='*40}")
    print(f"Attempt {i}/{max_retries}")
    try:
        path = kagglehub.dataset_download('moltean/fruits')
        print(f'SUCCESS: {path}')
        break
    except Exception as e:
        print(f'Failed: {e}')
        if i < max_retries:
            wait = min(i * 5, 30)
            print(f'Retrying in {wait}s...')
            time.sleep(wait)
