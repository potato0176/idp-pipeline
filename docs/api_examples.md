# API 使用範例 / API Examples

## 1. 上傳 PDF 文件進行處理

```bash
curl -X POST "http://localhost:8000/api/v1/process" \
  -F "file=@contract.pdf" \
  -F "output_format=markdown" \
  -F "languages=ch_tra,en" \
  -F "enable_vlm=true" \
  -F "chunk_size=512" \
  -F "store_in_vectordb=true"
```

**回應 (202 Accepted):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "Processing started for 'contract.pdf'",
  "created_at": "2025-01-15T10:30:00.000Z"
}
```

## 2. 查詢處理進度

```bash
curl "http://localhost:8000/api/v1/tasks/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

**處理中回應:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "processing",
  "current_stage": "vlm_enhance",
  "progress_pct": 50.0
}
```

**完成後回應:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "completed",
  "current_stage": "done",
  "progress_pct": 100.0,
  "result": {
    "output_format": "markdown",
    "content": "# 合約書\n\n## 第一條 ...",
    "metadata": {
      "source": "contract.pdf",
      "ocr_confidence": 0.92,
      "vlm_enhanced": true
    },
    "chunks_count": 15,
    "vector_ids": ["vec-001", "vec-002", "..."]
  }
}
```

## 3. 下載處理結果

```bash
curl -O "http://localhost:8000/api/v1/tasks/a1b2c3d4-.../download"
```

## 4. 語義搜尋

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "合約中的付款條件是什麼？",
    "top_k": 5
  }'
```

**回應:**
```json
{
  "query": "合約中的付款條件是什麼？",
  "results": [
    {
      "chunk_text": "付款條件：甲方應於簽約後三十日內支付...",
      "score": 0.89,
      "metadata": {"source": "contract.pdf", "chunk_index": 7}
    }
  ],
  "total": 1
}
```

## 5. Python 客戶端範例

```python
import httpx
import asyncio
import time


async def process_document(file_path: str):
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 上傳檔案
        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/process",
                files={"file": (file_path, f)},
                data={"output_format": "markdown", "enable_vlm": "true"},
            )
        task_id = resp.json()["task_id"]
        print(f"Task created: {task_id}")

        # 輪詢等待完成
        while True:
            status = await client.get(f"/api/v1/tasks/{task_id}")
            data = status.json()
            print(f"  Status: {data['status']} ({data.get('progress_pct', 0):.0f}%)")

            if data["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(2)

        if data["status"] == "completed":
            print(f"\nResult:\n{data['result']['content'][:500]}...")

asyncio.run(process_document("my_document.pdf"))
```
