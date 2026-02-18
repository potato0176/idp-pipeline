import httpx
import time

BASE = "http://localhost:8000"

# 加大 timeout
client = httpx.Client(timeout=120.0)

# 上傳圖片
with open("scan.png", "rb") as f:
    resp = client.post(
        f"{BASE}/api/v1/process",
        files={"file": ("scan.png", f, "image/png")},
        data={
            "output_format": "json",
            "enable_vlm": "true",
            "languages": "ch_tra,en",
        },
    )

print(resp.json())
task_id = resp.json()["task_id"]

# 輪詢結果
while True:
    status = client.get(f"{BASE}/api/v1/tasks/{task_id}").json()
    print(f"Status: {status['status']} ({status.get('progress_pct', 0)}%)")
    if status["status"] in ("completed", "failed"):
        if status.get("result"):
            print("\n=== Result ===")
            print(status["result"]["content"][:1000])
        elif status.get("error"):
            print(f"\nError: {status['error']}")
        break
    time.sleep(2)

client.close()
