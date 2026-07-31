# DevsRAG — Functional Requirements Document (FRD)

> **Platform Name**: DevsRAG  
> **Tagline**: Powered by the AntiGrav Engine — Zero weight, maximum context.  
> **Version**: 1.0.0 Enterprise Release

---

## 1. System Overview & Architecture

DevsRAG is an enterprise-grade Retrieval-Augmented Generation (RAG) platform built for intelligent document ingestion, layout parsing, vector index storage, and natural language querying with grounded, traceable citations.

### 1.1 Architectural Topology
```
[ Client Layer (Vite/React SPA) ]
       │
       ▼ (HTTP / REST API)
[ FastAPI Gateway Service ]
       ├── Metadata & Audit Store (SQLite / SQLModel)
       ├── Physical Storage (/backend/data/uploads)
       ├── Vector Database (ChromaDB Persistent Store)
       └── Processing & RAG Engine
             ├── Text Parsers (pypdf, python-docx, UTF-8 text)
             ├── Character Overlap Chunker (500-char window, 100-char overlap)
             ├── Embedding Vectorizer (Gemini text-embedding-004 / OpenAI / Local Hash)
             └── Synthesis Engine (Gemini 1.5 Flash / Grounded Prompts)
```

---

## 2. Scope, Document Ingestion & Lifecycle Management

### 2.1 Supported Document Formats
DevsRAG supports four standard document formats:
1. **PDF (`.pdf`)**: Native layout parsing via `pypdf`.
2. **DOCX (`.docx`)**: Office document extraction via `python-docx`.
3. **Plain Text (`.txt`)**: UTF-8 unstructured text files.
4. **Markdown (`.md`)**: Structured plain text and technical documentation.

### 2.2 Ingestion & Duplicate Guards
- **File Size Limit**: Maximum 25 MB per document file.
- **SHA-256 Content Hash Validation**: Computes file hash upon upload. Duplicates are flagged with HTTP 409 Conflict with optional force re-upload (`?overwrite=true`).
- **Asynchronous Non-Blocking Ingestion**: Returns HTTP 202 Accepted immediately. Document state transitions asynchronously: `pending` $\to$ `processing` $\to$ `ready` (or `failed`).

### 2.3 Lifecycle Operations
- **List Documents (`GET /api/v1/documents`)**: Paginated document library with status badges, chunk metrics, and upload timestamps.
- **Status Check (`GET /api/v1/documents/{id}`)**: Realtime document processing status.
- **Reprocess Document (`POST /api/v1/documents/{id}/reprocess`)**: Triggers clean re-extraction and re-vectorization.
- **Cascading Delete (`DELETE /api/v1/documents/{id}`)**: Atomically removes disk file, database metadata, and associated ChromaDB vector chunks.

---

## 3. RAG Pipeline, Grounding & Citation Strategy

### 3.1 Text Chunking & Vector Retrieval
- **Chunking Parameters**: 500 characters per chunk window with 100 characters overlap.
- **Top-K Retrieval**: 3 to 5 chunks (default $k=4$).
- **Similarity Threshold**: Adjusted vector similarity floor ensuring technical terms (e.g. `GEMINI_API_KEY`, configuration keys) are retrieved without being filtered.

### 3.2 System Prompt & Direct Answer Rules
The LLM synthesis prompt strictly enforces:
1. **Directness**: Answers the user's question directly in 1–2 clear sentences.
2. **Strict Grounding**: Uses ONLY the retrieved document context.
3. **Traceable Citations**: Appends inline citations cleanly (e.g. `[1]` or `[Source: filename.pdf, Page X]`).
4. **Missing Context Fallback**: If the context does not contain enough information, the system responds strictly with:  
   `"The uploaded documents do not contain relevant information to answer this query."`

---

## 4. Setup Instructions & Environment Configuration

### 4.1 Prerequisites
- Python 3.11+
- Virtual Environment (`backend/venv`)

### 4.2 Installation & Startup
```bash
# 1. Clone repository
git clone <repo_url>
cd "Devs project"

# 2. Set up virtual environment
python -m venv backend/venv

# Windows PowerShell:
.\backend\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# Linux/macOS:
source backend/venv/bin/activate
pip install -r backend/requirements.txt
```

### 4.3 Environment Variables (`.env`)
Create a `.env` file in the root directory:
```env
# Google Gemini API Key Integration
GEMINI_API_KEY=your_gemini_api_key_here

# Preferred Provider ("auto", "gemini", "openai")
EMBEDDING_PROVIDER=auto
LLM_PROVIDER=auto
```

### 4.4 Launch Server
```bash
PYTHONPATH=backend backend/venv/Scripts/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Navigate to **http://127.0.0.1:8000** to access the DevsRAG web platform.

---

## 5. Assumptions & Non-Functional Specifications

1. **Zero-Key Offline Fallback**: If no API key is provided in `.env`, DevsRAG operates in offline mode using local feature-hash vectorization and concise extractive synthesis.
2. **Single-Tenant Workspace Scope**: Assumes single-user / team workspace scope for document indexing.
3. **Security & Secrets**: `.env` is listed in `.gitignore` to ensure credentials are never committed.
