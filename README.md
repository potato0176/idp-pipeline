# IDP Pipeline API

> 智慧文件處理流水線 — Docling + EasyOCR + VLM (Gemma 3) + ChromaDB

PDF / 圖片 → 結構化文字 → 向量資料庫 → 語義搜尋

---

## 快速開始

### 1. 建立虛擬環境

```bash
cd D:\work_shop\idp-pipeline
python -m venv venv
```

啟動虛擬環境：

```powershell
# PowerShell（如果報錯，先執行下方的「常見問題 Q1」）
.\venv\Scripts\Activate.ps1

# 或用 CMD
venv\Scripts\activate.bat
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
copy .env.example .env
```

編輯 `.env`，根據你的硬體修改 VLM 模型：

```env
# GPU VRAM >= 16GB → gemma3:27b
# GPU VRAM >= 8GB  → gemma3:12b
# GPU VRAM >= 4GB  → gemma3:4b（推薦 GTX 1650 等級）
# GPU VRAM < 4GB   → gemma3:1b
VLM_MODEL=gemma3:4b
```

### 4. 安裝並啟動 Ollama

從 https://ollama.com/download/windows 下載安裝。

安裝後**重新開啟終端**（PATH 才會生效），然後拉取模型：

```bash
ollama pull gemma3:4b
```

### 5. 啟動 API 服務

```bash
uvicorn app.main:app --reload --port 8000
```

看到 `Uvicorn running on http://0.0.0.0:8000` 表示啟動成功。

### 6. 開始使用

打開瀏覽器訪問 **http://localhost:8000/docs** 即可使用 Swagger UI 測試所有 API。

---

## API 端點一覽

| 方法 | 端點 | 功能 |
|------|------|------|
| `POST` | `/api/v1/process` | 上傳 PDF/圖片，開始處理 |
| `GET` | `/api/v1/tasks/{task_id}` | 查詢處理進度 |
| `GET` | `/api/v1/tasks/{task_id}/download` | 下載處理結果 |
| `DELETE` | `/api/v1/tasks/{task_id}` | 刪除任務 |
| `POST` | `/api/v1/search` | 語義搜尋已處理的文件 |
| `GET` | `/api/v1/health` | 健康檢查 |

---

## 使用流程

### 方法一：Swagger UI（推薦）

1. 開啟 http://localhost:8000/docs
2. 展開 `POST /api/v1/process` → **Try it out**
3. 選擇檔案、設定參數 → **Execute**
4. 複製回傳的 `task_id`
5. 到 `GET /api/v1/tasks/{task_id}` 查詢進度
6. `status: completed` 後到 `/download` 下載結果
7. 到 `POST /api/v1/search` 進行語義搜尋

### 方法二：Python 腳本

在專案根目錄建立 `test_upload.py`：

```python
import httpx, time

BASE = "http://localhost:8000"
client = httpx.Client(timeout=120.0)

# 上傳檔案（改成你的檔名）
with open("your_file.pdf", "rb") as f:
    resp = client.post(
        f"{BASE}/api/v1/process",
        files={"file": ("your_file.pdf", f, "application/pdf")},
        data={"output_format": "markdown", "enable_vlm": "true"},
    )

task_id = resp.json()["task_id"]
print(f"Task: {task_id}")

# 輪詢結果
while True:
    status = client.get(f"{BASE}/api/v1/tasks/{task_id}").json()
    print(f"Status: {status['status']} ({status.get('progress_pct', 0)}%)")
    if status["status"] in ("completed", "failed"):
        if status.get("result"):
            print(status["result"]["content"][:500])
        break
    time.sleep(2)
```

```bash
python test_upload.py
```

### 方法三：curl（PowerShell 中要用 curl.exe）

```powershell
# 上傳
curl.exe -X POST "http://localhost:8000/api/v1/process" -F "file=@test.pdf" -F "output_format=markdown"

# 查詢進度
curl.exe http://localhost:8000/api/v1/tasks/你的task_id

# 語義搜尋
curl.exe -X POST "http://localhost:8000/api/v1/search" -H "Content-Type: application/json" -d "{\"query\": \"LLM是什麼\", \"top_k\": 5}"

# 健康檢查
curl.exe http://localhost:8000/api/v1/health
```

---

## 處理結果存放位置

| 位置 | 內容 | 持久化 |
|------|------|--------|
| `data/uploads/` | 上傳的原始檔案 | 是 |
| `data/outputs/` | 處理結果 (.md / .json) + 元資料 (_meta.json) | 是 |
| `data/chroma_db/` | 向量資料庫（切片 + 嵌入向量） | 是 |

---

## .env 設定說明

```env
# === 應用 ===
APP_NAME=IDP-Pipeline        # 應用名稱
APP_ENV=development           # 環境（development / production）
DEBUG=true                    # 除錯模式

# === VLM 模型 ===
VLM_API_BASE=http://localhost:11434/v1   # Ollama API 地址
VLM_MODEL=gemma3:4b                       # 模型名稱（按 GPU 選擇）
VLM_TIMEOUT=120                           # VLM 超時秒數

# === OCR ===
OCR_LANGUAGES=ch_tra,en       # 辨識語言（繁中+英文）
OCR_GPU=true                  # 是否使用 GPU 加速 OCR

# === 向量資料庫 ===
CHROMA_PERSIST_DIR=./data/chroma_db      # ChromaDB 儲存路徑
EMBEDDING_MODEL=all-MiniLM-L6-v2         # 嵌入模型

# === 切片 ===
CHUNK_SIZE=512                # 每個切片最大字元數
CHUNK_OVERLAP=50              # 切片重疊字元數

# === 檔案 ===
UPLOAD_DIR=./data/uploads     # 上傳目錄
OUTPUT_DIR=./data/outputs     # 輸出目錄
MAX_FILE_SIZE_MB=50           # 最大檔案大小 (MB)
```

---

## 執行測試

```bash
pytest tests/ -v
```

預期結果：17/17 全部通過。

---

## Docker 部署

```bash
# 建置
docker build -t idp-pipeline .

# 啟動（連接本機 Ollama）
docker run -p 8000:8000 -e VLM_API_BASE=http://host.docker.internal:11434/v1 idp-pipeline
```

---

## 常見問題

### Q1: PowerShell 無法啟動虛擬環境

```
running scripts is disabled on this system
```

**解法：**

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q2: ollama 命令找不到

**解法：** 安裝 Ollama 後必須**重新開啟終端**（關掉 VSCode 再重開），PATH 才會生效。

臨時修復：

```powershell
$env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
```

### Q3: PowerShell 的 curl 報錯

PowerShell 的 `curl` 是 `Invoke-WebRequest` 的別名，不是真正的 curl。

**解法：** 改用 `curl.exe`（加 .exe），或直接用 Swagger UI。

### Q4: 上傳檔案超時

**解法：** Python 腳本中加大 timeout：

```python
client = httpx.Client(timeout=120.0)
```

### Q5: 第一次處理 PDF 卡在 10%

Docling 首次運行需要下載 AI 模型（約 1-2GB），請耐心等待 5-10 分鐘。

### Q6: VLM 模型太大跑不動

按你的 GPU VRAM 選擇合適的模型：

| GPU VRAM | 建議模型 | 拉取指令 |
|----------|----------|----------|
| >= 16GB | gemma3:27b | `ollama pull gemma3:27b` |
| >= 8GB | gemma3:12b | `ollama pull gemma3:12b` |
| >= 4GB | gemma3:4b | `ollama pull gemma3:4b` |
| < 4GB | gemma3:1b | `ollama pull gemma3:1b` |

記得同步修改 `.env` 中的 `VLM_MODEL`。

---

## 技術架構

```
Client (PDF/圖片)
    │
    ▼
FastAPI (routes.py) ──── 非同步接收，返回 task_id
    │
    ▼ BackgroundTasks
Pipeline (pipeline.py) ── 六階段流水線
    │
    ├─ Stage 1: Docling ─── PDF 結構化解析
    ├─ Stage 2: EasyOCR ─── 光學字元辨識
    ├─ Stage 3: VLM ─────── Gemma 3 增強（可選）
    ├─ Stage 4: Chunking ── 文本切片
    ├─ Stage 5: ChromaDB ── 向量嵌入儲存
    └─ Stage 6: Save ────── 結果存檔 (.md/.json)
    │
    ▼
data/outputs/ ── 處理結果
data/chroma_db/ ── 向量資料庫 ──→ POST /search 語義搜尋
```