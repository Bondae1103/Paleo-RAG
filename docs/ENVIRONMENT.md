# ENVIRONMENT.md — System & Dependency Baseline

Recorded on: 2026-10-13 (Phase P0 Baseline)

## 1. Operating System & Host Environment
- **OS**: Microsoft Windows 11 Home Single Language (64-bit)
- **Kernel / OS Version**: 10.0.26200 (Build 26200)
- **Shell**: PowerShell 5.1 / PowerShell 7
- **Git Version**: 2.53.0.windows.2
- **Baseline Git Commit**: `e7c86bc946f9f27af7e9372683d24276d6a0d303` (branch `main`)

## 2. Runtimes & Interpreters
- **Python (Virtual Environment)**: Python 3.11.9 (`c:\Users\Anoop\Documents\Projects\Tech\Ongoing\paleo_rag\.venv\Scripts\python.exe`)
- **Node.js**: v22.14.0
- **npm**: 10.9.2
- **Web Browser Available for Headless Automation**: Google Chrome (`C:\Program Files\Google\Chrome\Application\chrome.exe`), Microsoft Edge (`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`)

## 3. Python Virtual Environment Packages (`pip list`)
| Package | Version |
|---|---|
| amqp | 5.3.1 |
| annotated-doc | 0.0.5 |
| annotated-types | 0.8.0 |
| anthropic | 0.39.0 |
| anyio | 4.15.1 |
| billiard | 4.2.4 |
| biopython | 1.84 |
| celery | 5.6.3 |
| certifi | 2026.7.22 |
| charset-normalizer | 3.5.1 |
| click | 8.5.0 |
| click-didyoumean | 0.3.1 |
| click-plugins | 1.1.1.2 |
| click-repl | 0.3.0 |
| cloudpickle | 3.1.2 |
| colorama | 0.4.6 |
| distro | 1.9.0 |
| fastapi | 0.141.1 |
| filelock | 3.32.5 |
| fsspec | 2026.7.0 |
| grpcio | 1.83.1 |
| h11 | 0.16.0 |
| h2 | 4.4.1 |
| hpack | 4.2.0 |
| httpcore | 1.0.9 |
| httptools | 0.8.0 |
| httpx | 0.28.1 |
| huggingface_hub | 0.36.2 |
| hyperframe | 6.1.0 |
| idna | 3.19 |
| iniconfig | 2.3.0 |
| Jinja2 | 3.1.6 |
| jiter | 0.16.0 |
| joblib | 1.6.0 |
| kombu | 5.6.2 |
| MarkupSafe | 3.0.3 |
| mpmath | 1.3.0 |
| narwhals | 2.25.0 |
| networkx | 3.6.1 |
| numpy | 2.4.6 |
| packaging | 26.3 |
| pillow | 12.3.0 |
| pip | 26.2.1 |
| pluggy | 1.6.0 |
| portalocker | 3.2.0 |
| prompt_toolkit | 3.0.53 |
| protobuf | 7.36.1 |
| pydantic | 2.13.5 |
| pydantic_core | 2.46.5 |
| pydantic-settings | 2.15.0 |
| Pygments | 2.21.0 |
| pymupdf | 1.28.2 |
| pytest | 9.1.1 |
| pytest-asyncio | 1.4.0 |
| python-dateutil | 2.9.0.post0 |
| python-dotenv | 1.2.3 |
| python-multipart | 0.0.32 |
| pywin32 | 312 |
| PyYAML | 6.0.3 |
| qdrant-client | 1.19.0 |
| rank-bm25 | 0.2.2 |
| redis | 8.1.0 |
| regex | 2026.9.3 |
| requests | 2.34.2 |
| respx | 0.23.1 |
| safetensors | 0.8.0 |
| scikit-learn | 1.9.0 |
| scipy | 1.17.1 |
| sentence-transformers | 3.2.1 |
| setuptools | 84.0.0 |
| six | 1.17.0 |
| sniffio | 1.3.1 |
| starlette | 1.6.0 |
| sympy | 1.14.0 |
| threadpoolctl | 3.6.0 |
| tokenizers | 0.22.2 |
| torch | 2.14.0 |
| tqdm | 4.70.0 |
| transformers | 4.57.6 |
| typing_extensions | 4.16.0 |
| typing-inspection | 0.4.4 |
| tzdata | 2026.3 |
| tzlocal | 5.4.4 |
| urllib3 | 2.7.0 |
| uvicorn | 0.52.4 |
| vine | 5.1.0 |
| watchfiles | 1.2.0 |
| wcwidth | 0.8.3 |
| websockets | 17.1 |

## 4. Frontend Dependencies (`package.json`)
- **Build tool**: Vite 7.3.6
- **UI Framework**: React 19.3.0, ReactDOM 19.3.0
- **Language**: TypeScript 5.6.3
- **Styling**: Tailwind CSS v4.3.3 (`@tailwindcss/vite` 4.3.3)
- **UI Primitives**: Radix UI (dialog, dropdown, tabs, tooltip, etc.)
- **Icons**: Lucide React 0.453.0
- **Routing**: Wouter 3.11.0
- **Browser Automation (Installed for P0 baseline)**: Playwright 1.58.x (driving local Chrome)

## 5. Storage & Vector DB Configuration
- **Vector DB**: Qdrant running in embedded local storage mode (`QDRANT_USE_LOCAL_MODE=true`, `QDRANT_LOCAL_PATH=./data/qdrant_storage`)
- **Collection**: `paleo_chunks` (Cosine distance, 768 dimensions)
- **Local Cache**: DiskCache (`data/bio_cache`)
