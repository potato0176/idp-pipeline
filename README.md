# 🔄 Intelligent Document Processing (IDP) Pipeline API

> 整合式智慧文件處理流水線 — 結合 Docling、EasyOCR 與 VLM (Gemma 3 27b)，提供非同步 PDF/圖片處理、Markdown/JSON 輸出，並自動將切片存入向量資料庫。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 目錄 / Table of Contents

1. [系統架構 Architecture](#系統架構-architecture)
2. [功能特色 Features](#功能特色-features)
3. [專案結構 Project Structure](#專案結構-project-structure)
4. [環境需求 Requirements](#環境需求-requirements)
5. [安裝與設定 Installation](#安裝與設定-installation)
6. [使用方式 Usage](#使用方式-usage)
7. [API 文件 API Documentation](#api-文件-api-documentation)
8. [測試 Testing](#測試-testing)
9. [部署 Deployment](#部署-deployment)

---

## 系統架構 Architecture

```
┌──────────────┐     ┌──────────────────────────────────────────────┐
│   Client     │     │           IDP Pipeline API (FastAPI)         │
│  (PDF/Image) │────▶│                                              │
└──────────────┘     │  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
                     │  │ Docling  │  │ EasyOCR │  │ VLM (Gemma) │  │
                     │  │ Parser   │  │ Engine  │  │ Enhancer    │  │
                     │  └────┬─────┘  └────┬────┘  └──────┬──────┘  │
                     │       │             │              │          │
                     │       ▼             ▼              ▼          │
                     │  ┌──────────────────────────────────────┐     │
                     │  │     Async Processing Pipeline         │     │
                     │  │  Ingest → Parse → OCR → VLM Enhance  │     │
                     │  └──────────────────┬───────────────────┘     │
                     │                     │                         │
                     │                     ▼                         │
                     │  ┌──────────────────────────────────────┐     │
                     │  │   Chunking & Embedding Engine         │     │
                     │  │  (RecursiveCharacterTextSplitter)     │     │
                     │  └──────────────────┬───────────────────┘     │
                     │                     │                         │
                     │                     ▼                         │
                     │  ┌──────────────────────────────────────┐     │
                     │  │   Vector Store (ChromaDB)             │     │
                     │  └──────────────────────────────────────┘     │
                     └──────────────────────────────────────────────┘
```

### 處理流程 Processing Pipeline

```
PDF/圖片上傳 → 文件解析 (Docling) → OCR 辨識 (EasyOCR)
    → VLM 增強理解 (Gemma 3 27b) → 結構化輸出 (Markdown/JSON)
    → 文本切片 (Chunking) → 向量嵌入 (Embedding)
    → 存入向量資料庫 (ChromaDB)
```

---

## 功能特色 Features

- **非同步處理**：基於 FastAPI + asyncio，支援並行處理多份文件
- **多格式支援**：PDF（含掃描件）、PNG、JPG、TIFF 等
- **三階段流水線**：
  - **Docling**：結構化 PDF 解析（表格、標題、段落）
  - **EasyOCR**：多語言 OCR（支援中英文）
  - **VLM (Gemma 3 27b)**：視覺語言模型增強文件理解
- **智慧切片**：RecursiveCharacterTextSplitter 自動分割文本
- **向量儲存**：ChromaDB 自動嵌入與持久化
- **任務追蹤**：非同步任務佇列，支援狀態查詢與回呼
- **雙格式輸出**：Markdown 與 JSON 格式可選

---

## 專案結構 Project Structure

```
idp-pipeline/
│
├── README.md                   # 專案說明文件（本文件）
├── LICENSE                     # MIT 授權條款
├── .gitignore                  # Git 忽略規則
├── .env.example                # 環境變數範本
├── requirements.txt            # Python 依賴套件
├── pyproject.toml              # 專案元資料與工具設定
│
├── app/                        # 🔧 主要應用程式碼
│   ├── __init__.py
│   ├── main.py                 # FastAPI 應用入口 & 生命週期管理
│   │
│   ├── api/                    # 📡 API 路由層
│   │   ├── __init__.py
│   │   ├── routes.py           # API 端點定義（上傳、查詢、下載）
│   │   └── dependencies.py     # 依賴注入（服務實例）
│   │
│   ├── core/                   # ⚙️ 核心設定
│   │   ├── __init__.py
│   │   ├── config.py           # 應用設定（Pydantic Settings）
│   │   └── logging_config.py   # 日誌設定
│   │
│   ├── models/                 # 📦 資料模型
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic 請求/回應模型
│   │
│   ├── services/               # 🔄 業務邏輯層（核心服務）
│   │   ├── __init__.py
│   │   ├── pipeline.py         # 流水線協調器（主要服務）
│   │   ├── docling_parser.py   # Docling 文件解析服務
│   │   ├── ocr_service.py      # EasyOCR 服務封裝
│   │   ├── vlm_service.py      # VLM (Gemma 3) 服務封裝
│   │   ├── chunking_service.py # 文本切片服務
│   │   └── vector_store.py     # ChromaDB 向量資料庫服務
│   │
│   └── utils/                  # 🛠️ 工具函式
│       ├── __init__.py
│       ├── file_handler.py     # 檔案上傳/暫存處理
│       └── task_manager.py     # 非同步任務管理器
│
├── tests/                      # 🧪 測試
│   ├── __init__.py
│   ├── conftest.py             # Pytest 共用 fixtures
│   ├── test_api.py             # API 端點測試
│   ├── test_pipeline.py        # 流水線整合測試
│   └── test_services.py        # 各服務單元測試
│
├── configs/                    # 📁 設定檔
│   └── default.yaml            # 預設設定（模型參數等）
│
├── scripts/                    # 📜 輔助腳本
│   └── setup_env.sh            # 環境初始化腳本
│
├── docs/                       # 📖 額外文件
│   └── api_examples.md         # API 使用範例
│
└── .github/                    # 🔄 GitHub 設定
    └── workflows/
        └── ci.yml              # GitHub Actions CI/CD
```

### 📂 各資料夾用途說明

| 資料夾 | 放什麼 | 說明 |
|--------|--------|------|
| `app/` | 所有 Python 原始碼 | 主要應用程式，包含 API、服務、模型 |
| `app/api/` | 路由與依賴注入 | FastAPI 的 Router 定義 |
| `app/core/` | 設定檔 | 環境變數讀取、日誌設定 |
| `app/models/` | Pydantic 模型 | 請求/回應的資料結構定義 |
| `app/services/` | 核心業務邏輯 | Docling、OCR、VLM、Chunking、VectorStore |
| `app/utils/` | 通用工具 | 檔案處理、任務管理 |
| `tests/` | 所有測試檔案 | 單元測試與整合測試 |
| `configs/` | YAML 設定檔 | 模型參數、分片設定等 |
| `scripts/` | Shell 腳本 | 環境初始化、資料庫遷移等 |
| `docs/` | 額外文件 | API 使用範例、架構圖等 |
| `.github/workflows/` | CI/CD 設定 | GitHub Actions 自動測試 |

---

## 環境需求 Requirements

- Python 3.10+
- CUDA GPU（建議，用於 VLM 推論；CPU 亦可但較慢）
- 8GB+ RAM（VLM 推論建議 16GB+）

### 主要依賴

| 套件 | 用途 |
|------|------|
| `fastapi` + `uvicorn` | Web API 框架 |
| `docling` | PDF 結構化解析 |
| `easyocr` | 多語言 OCR 引擎 |
| `openai` / `ollama` | VLM API 呼叫（Gemma 3 27b） |
| `langchain-text-splitters` | 文本切片 |
| `chromadb` | 向量資料庫 |
| `sentence-transformers` | 文本嵌入模型 |
| `python-multipart` | 檔案上傳支援 |
| `pydantic-settings` | 設定管理 |

---

## 安裝與設定 Installation

### 1. Clone 專案

```bash
git clone https://github.com/<your-username>/idp-pipeline.git
cd idp-pipeline
```

### 2. 建立虛擬環境

```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

### 3. 安裝依賴

```bash
pip install -r requirements.txt
```

### 4. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入您的設定（VLM API endpoint 等）
```

### 5. 啟動 VLM 服務（使用 Ollama）

```bash
# 安裝 Ollama: https://ollama.ai
ollama pull gemma3:27b
ollama serve
```

### 6. 啟動 API 服務

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文件自動產生：`http://localhost:8000/docs`

---

## 使用方式 Usage

### 上傳文件處理

```bash
# 上傳 PDF 檔案
curl.exe -X POST "http://localhost:8000/api/v1/process" \
  -F "file=@document.pdf" \
  -F "output_format=markdown"

# 上傳圖片
curl.exe -X POST "http://localhost:8000/api/v1/process" \
  -F "file=@scan.png" \
  -F "output_format=json" \
  -F "languages=ch_tra,en"
```

### 查詢處理狀態

```bash
curl.exe http://localhost:8000/api/v1/tasks/你的task_id
```

### 查詢向量資料庫

```bash
curl.exe -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "合約中的付款條件", "top_k": 5}'
```

---

## API 文件 API Documentation

| 方法 | 端點 | 說明 |
|------|------|------|
| `POST` | `/api/v1/process` | 上傳文件並啟動處理流水線 |
| `GET` | `/api/v1/tasks/{task_id}` | 查詢處理任務狀態與結果 |
| `GET` | `/api/v1/tasks/{task_id}/download` | 下載處理結果 |
| `POST` | `/api/v1/search` | 語義搜尋向量資料庫 |
| `GET` | `/api/v1/health` | 服務健康檢查 |
| `DELETE` | `/api/v1/tasks/{task_id}` | 刪除任務及相關資料 |

詳細範例請見 [docs/api_examples.md](docs/api_examples.md)

---

## 測試 Testing

```bash
# 執行全部測試
pytest tests/ -v

# 執行特定測試
pytest tests/test_api.py -v

# 顯示覆蓋率
pytest tests/ --cov=app --cov-report=term-missing
```

---

## 部署 Deployment

### Docker（可選）

```bash
docker build -t idp-pipeline .
docker run -p 8000:8000 --gpus all idp-pipeline
```

### 生產環境

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 授權 License

MIT License — 詳見 [LICENSE](LICENSE)
