# DevsRAG — Intelligent Document RAG Assistant

> **Domain:** Artificial Intelligence & Machine Learning (AIML)  
> **Tagline:** *Powered by the AntiGrav Engine — Zero weight, maximum context.*

DevsRAG is a state-of-the-art Intelligent Document Understanding and Search Platform. Built for engineering and research teams, DevsRAG processes multi-format documents (PDF, DOCX, TXT, MD), performs zero-latency hybrid vector retrieval backed by ChromaDB, and synthesizes grounded, direct natural-language answers using Google Gemini LLMs with traceable citations.

---

## ⚡ Key Features

- 📌 **Grounded Inline Citations & Citation Inspector Drawer**: Every synthesized response includes direct inline citation tags (`[Source: policy.pdf, p. 2]`). Clicking any citation chip opens a floating slide-over modal drawer displaying the exact raw text chunk retrieved from vector memory.
- ⚖️ **Document Comparison ("Diff") Mode**: Compare specifications and features between different file versions (e.g. `devsrag_v1_specs.txt` vs `devsrag_v2_specs.txt`). Generates structured HTML Markdown comparison tables contrasting actual technical content (RAM, ports, limits, latency, specs) rather than superficial metadata.
- 🧠 **Multi-Turn Conversational Memory & Contextual Re-writing**: Maintains a rolling 5-turn chat context. Uses Gemini to resolve vague terms and pronouns (*"what about that file?"*, *"summarize it"*) into explicit, standalone vector search queries before retrieval.
- ⏱️ **Workspace Metadata Aggregation & Dynamic Timestamps**: Query upload dates, total page counts, file sizes, and workspace statistics in local browser time (`DD MMM, hh:mm am/pm`).
- 📁 **Scanned PDF & Image OCR Fallback**: Automatically detects scanned or image-only PDFs with 0 selectable text and routes pages to an OCR fallback pipeline (Pytesseract / Gemini Vision API) so scanned documents never fail.
- 🔄 **Automatic Overwrite & In-App Toast System**: Uploading duplicate document hashes or filenames automatically purges old vectors and re-indexes cleanly without 400/409 errors. Replaces browser alerts with non-intrusive toast pop-ups.
- 📊 **Interactive Bento Grid Dark-Mode UI**: Features frosted glass card borders, glowing hover effects, prompt pills, and clear chat/export session log controls.

---

## 🛠 Tech Stack

- **Backend Framework**: Python 3.11+, FastAPI, Uvicorn, SQLModel (SQLite database).
- **Vector Database**: ChromaDB (384-dimensional dense vector store with sub-word n-gram feature hashing).
- **AI & LLM Integration**: Google Gemini 2.0 Flash (`google-genai` SDK v2), OpenAI fallback.
- **Document Processing**: `pypdf`, `pdfplumber`, `python-docx`, `pdf2image`, `pytesseract`.
- **Frontend SPA**: HTML5, JavaScript (ES6+), Vanilla CSS, Tailwind CSS CDN, Google Fonts (`Outfit`, `JetBrains Mono`).

---

## 🏗 System Architecture & Workflow

```
                  +-----------------------------------+
                  |   Document Upload (PDF/DOCX/TXT)   |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |  ParserService & OCR Fallback     |
                  |  (Text Extraction & Page Split)   |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |  ChunkerService & Embedding       |
                  |  (500-char Window / 384-Dim Vecs) |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |    ChromaDB Vector Database       |
                  |    (Indexed Document Chunks)      |
                  +-----------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  User Query Request   |                       | Contextual Re-writer  |
|  (Frontend SPA)       |                       | (Pronoun Resolution)  |
+-----------------------+                       +-----------------------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                  +-----------------------------------+
                  | Hybrid Top-K Vector Retrieval     |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |  Gemini Grounded LLM Synthesis    |
                  |  (Dual Query / Diff / Summary)    |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  | Grounded Answer & Citation Drawer |
                  +-----------------------------------+
```

---

## 🚀 Local Installation & Setup

### Prerequisites

- Python 3.10 or higher installed.
- Git installed.
- (Optional) A Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).

---

### Step 1: Clone Repository & Create Virtual Environment

```bash
# Clone repository
git clone https://github.com/your-username/devsrag.git
cd devsrag

# Create Python virtual environment
python -m venv backend/venv

# Activate virtual environment (Windows PowerShell)
.\backend\venv\Scripts\Activate.ps1

# Activate virtual environment (Linux / macOS)
# source backend/venv/bin/activate
```

---

### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 3: Configure Environment Variables

Create a `.env` file in the root or `backend/` directory and add your Google Gemini API key:

```env
PROJECT_NAME="DevsRAG — Intelligent Document Understanding Platform"
GEMINI_API_KEY="your_actual_gemini_api_key_here"
```

> **Note:** If `GEMINI_API_KEY` is omitted or quota limits occur (HTTP 429), DevsRAG automatically switches to its offline deterministic synthesis engine so queries and test suites never break.

---

### Step 4: Run Application Local Server

```bash
# Start FastAPI backend server from root directory
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```

Open your browser and navigate to **`http://127.0.0.1:8000`** to access the DevsRAG UI.

---

### Step 5: Run Automated Integration Test Suite

To verify system health, DB cascade cleanups, document parsing, and query endpoints:

```bash
python backend/tests/test_backend.py
```

---

## 📑 API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents` | Upload & queue async document vector indexing (`overwrite=true` supported). |
| `GET` | `/api/v1/documents` | List all workspace documents with status, pages, size, and upload timestamps. |
| `GET` | `/api/v1/documents/{id}` | Get detailed document metadata by ID. |
| `DELETE` | `/api/v1/documents/{id}` | Remove document record, physical file, and associated ChromaDB vector chunks. |
| `POST` | `/api/v1/query` | Submit natural-language question, metadata query, or diff comparison with chat history. |
| `GET` | `/api/v1/health` | Health check endpoint returning vector store connection status and chunk count. |

---

## 📜 License

Distributed under the MIT License. Built for AntiGrav AIML Document Reasoning Benchmarks.
