# 🌳 FarmerVerify AI

### AI-Powered Multilingual Document Verification Platform

**An enterprise-grade AI platform for automated document intake, quality analysis, multilingual OCR extraction, fuzzy record matching, and fraud verification.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9-red.svg)](https://opencv.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Overview](#-project-overview) • [Key Features](#-key-features) • [Architecture](#-architecture-overview) • [Installation](#-installation-guide) • [Running the App](#-running-the-application) • [API Reference](#-api-endpoints) • [Interfaces](#-user-interfaces) • [Testing](#-testing) • [Security](#-security-note)

---

## ⚠️ Disclaimer & Public Safety Note

- **All data in this repository is synthetic.** Sample beneficiary records, mock documents, and database seeds are randomly generated for demonstration purposes and do not correspond to any real person or organization.
- This repository is **100% open-source**. All proprietary credentials, tokens, and corporate references have been stripped or replaced with safe placeholders.
- When deploying with real data, operators are responsible for compliance with applicable data protection legislation, including India's **Digital Personal Data Protection (DPDP) Act, 2023**.
- Supply your **own credentials** via a local `.env` file (see [`.env.example`](.env.example)).

---

## 📋 Table of Contents

1. [Project Title](#-farmerverify-ai)
2. [Project Overview](#-project-overview)
3. [Key Features](#-key-features)
4. [Technologies Used](#-technologies-used)
5. [Architecture Overview](#-architecture-overview)
6. [Installation Guide](#-installation-guide)
7. [Environment Setup](#-environment-setup)
8. [Running Backend](#-running-the-backend)
9. [User Interfaces](#-user-interfaces)
10. [API Endpoints](#-api-endpoints)
11. [Folder Structure](#-folder-structure)
12. [Usage Instructions](#-usage-instructions)
13. [Project Workflow](#-project-workflow)
14. [Current Functionality](#-current-functionality)
15. [Future Enhancements](#-future-enhancements)
16. [License](#-license)
17. [Contribution Guidelines](#-contribution-guidelines)
18. [Security Note](#-security-note)
19. [Contact Information](#-contact-information)

---

## 🔍 Project Overview

Document verification in rural field operations is heavily bottlenecked by manual review, poor smartphone camera conditions (blur, glare, improper angles), mixed script documents (Hindi, Marathi, English), and lack of immediate user feedback.

**FarmerVerify AI** solves this by providing a unified, end-to-end automated pipeline:
- **Instant Pre-Upload Quality Check**: Evaluates blur, brightness, and document skew in real time using OpenCV.
- **Multilingual OCR & Field Extraction**: Combines Vision AI and EasyOCR/Tesseract engines to extract structured fields from bank passbooks, land extracts (7/12), and identity cards.
- **Fuzzy Record Matching**: Cross-checks extracted data against database records using RapidFuzz, handling transliterated name variations (Devanagari to Latin).
- **Automated Fraud Detection**: Runs Error Level Analysis (ELA) and perceptual hashing to catch digital edits and duplicate submissions.
- **Web User Interfaces**: Provides an interactive Web Chatbot (`/chat`) for document intake and an Admin Review Dashboard (`/admin`) for field staff oversight.

---

## ✨ Key Features

- **📸 Image Quality Assessment Engine** (`backend/services/quality_checker.py`): Evaluates Laplacian variance for blur, brightness distributions for glare/under-exposure, and document contour skew.
- **📄 Multilingual Document Intelligence** (`backend/services/ocr_engine.py`): Extracts structured fields from typed and handwritten documents in Hindi, Marathi, and English.
- **✅ Phonetic & Transliteration Matching** (`backend/services/fuzzy_matcher.py`): Performs token-set matching and Levenshtein distance scoring against database records.
- **🚨 Image Manipulation & Fraud Guard** (`backend/services/fraud_detector.py`): Detects compressed edit artifacts via Error Level Analysis (ELA) and prevents duplicate re-submissions via dhash perceptual fingerprinting.
- **🎯 Confidence & Risk Scoring Model** (`backend/models/validation_result.py`): Computes multi-factor overall verification confidence and auto-approval recommendation thresholds.
- **📊 Admin Review Dashboard** (`dashboard/`): Built-in web dashboard hosted at `/admin` for reviewing flagged documents, viewing confidence metrics, and exporting structured data.
- **💬 Web Chatbot Interface** (`chatbot/`): Interactive web assistant hosted at `/chat` for conversational document upload and immediate quality feedback.
- **📥 Structured JSON Data Exporter** (`backend/api/extract.py`): Standardized JSON extraction endpoints for integration with external record databases.

---

## 🛠 Technologies Used

- **Core Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic
- **Computer Vision**: OpenCV (`opencv-python`), Pillow, NumPy
- **OCR Engine**: Vision LLM APIs, EasyOCR, PyMuPDF (`fitz`), Tesseract OCR
- **Fuzzy Matching**: RapidFuzz
- **Frontend Interfaces**: Vanilla HTML5, CSS3, JavaScript ES6+, Lucide Icons
- **Database & Storage**: PostgreSQL / Supabase client, JSON Document Store
- **Testing & Quality**: pytest, httpx

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT INTERFACES                    │
│      Web Chatbot (/chat)  │  Admin Dashboard (/admin)    │
│                  REST API HTTP Clients                  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                  FASTAPI BACKEND SERVER                 │
│                      (backend/main.py)                  │
│                                                         │
│  ┌───────────────────────┐   ┌───────────────────────┐  │
│  │    QUALITY CHECKER    │   │      OCR ENGINE       │  │
│  │  • Blur Detection     │   │  • Multilingual OCR   │  │
│  │  • Brightness Check   │   │  • Field Extraction   │  │
│  │  • Skew & Contour     │   │  • Vision LLM Engine  │  │
│  └───────────┬───────────┘   └───────────┬───────────┘  │
│              │                           │              │
│              └─────────────┬─────────────┘              │
│                            │                            │
│                            ▼                            │
│              ┌───────────────────────────┐              │
│              │     VALIDATION ENGINE     │              │
│              │  • Field Normalization    │              │
│              │  • RapidFuzz Matcher      │              │
│              │  • ELA Fraud Detection    │              │
│              └─────────────┬─────────────┘              │
└────────────────────────────┼────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                        │
│          Document Store  │  PostgreSQL / Database       │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation Guide

### Prerequisites

- **Python 3.10+**
- **Git**
- **Tesseract OCR** (Optional, for local Tesseract fallback)

### 1. Clone the Repository

```bash
git clone https://github.com/open-source/farmerverify-ai.git
cd farmerverify-ai
```

### 2. Create and Activate Virtual Environment

```bash
# On Linux/macOS
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Environment Setup

Copy `.env.example` to create your local `.env` configuration file:

```bash
cp .env.example .env
```

Configure key variables in `.env`:

```env
# Application Server
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=True

# OCR & Vision API (Mock or Live)
OCR_MODE=mock
OCR_MODEL=gpt-4.1
OCR_API_KEY=your_vision_api_key_here

# Database
DATABASE_MODE=mock
DATABASE_URL=postgresql://user:password@localhost:5432/farmerverify
```

---

## 🖥️ Running the Application

### Running the Backend Server

Start the FastAPI application using `run.py` or `uvicorn`:

```bash
python run.py
```

Or using Uvicorn directly:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, access:
- **Root Health Status**: `http://localhost:8000/`
- **Interactive Swagger API Docs**: `http://localhost:8000/docs`
- **ReDoc API Documentation**: `http://localhost:8000/redoc`

---

## 🌐 User Interfaces

FarmerVerify AI includes built-in web interfaces hosted directly by the FastAPI backend:

1. **Web Chatbot Interface**: `http://localhost:8000/chat`
   - Conversational document submission interface.
   - Real-time image preview and quality score feedback.
   - Multi-language interaction support.

2. **Admin Review Dashboard**: `http://localhost:8000/admin`
   - Real-time review queue of submitted documents.
   - Quality score visualizations, extracted fields inspector, and manual override controls.
   - Verified data export to JSON/CSV format.

---

## 📡 API Endpoints

### Core Document Pipeline (`/api/v1`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service health check and navigation links |
| `POST` | `/api/v1/upload/document` | Upload document for quality check, OCR, and validation |
| `GET` | `/api/v1/status/{document_id}` | Retrieve processing status and extracted data |
| `POST` | `/api/v1/validate` | Validate raw extracted fields against record schema |
| `GET` | `/api/v1/extract/{request_id}/json` | Export structured JSON for verified documents |

### Dashboard & Admin API (`/api/v1/dashboard`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboard/stats` | Overview processing statistics and approval rates |
| `GET` | `/api/v1/dashboard/documents` | List recent document verification requests |
| `GET` | `/api/v1/dashboard/documents/{request_id}` | Get detailed document inspection record |
| `PUT` | `/api/v1/dashboard/documents/{request_id}/status` | Manually approve or reject document status |
| `POST` | `/api/v1/dashboard/documents/{request_id}/ai-review` | Trigger secondary AI re-inspection |
| `GET` | `/api/v1/dashboard/export/verified` | Export all verified beneficiary records |

---

## 📂 Folder Structure

```
farmerverify-ai/
│
├── backend/                  # FastAPI Application Core
│   ├── main.py               # Application factory & static mounts
│   ├── config.py             # Configuration loader & Pydantic settings
│   ├── api/                  # API Routers (upload, status, dashboard, extract)
│   ├── database/             # Document store & synthetic data seeder
│   ├── models/               # Pydantic models (Document, OCRResult, QualityResult)
│   ├── services/             # Quality Checker, OCR Engine, Fuzzy Matcher, Fraud Detector
│   └── utils/                # Loggers, image handlers, and helper utilities
│
├── cv_engine/                # Computer Vision module directory
├── ocr_engine/               # Multilingual OCR module directory
├── dashboard/                # Admin Dashboard Web App (HTML, CSS, JS, Lucide)
├── chatbot/                  # Web Chatbot App (HTML, CSS, JS)
├── whatsapp_bot/             # Reserved for future messaging channel integration
├── deployment/               # Deployment scripts directory
├── tests/                    # Unit and integration test suite
├── .env.example              # Environment variable template
├── .gitignore                # Version control ignore rules
├── LICENSE                   # Open-source MIT License
├── NOTICE.md                 # Dependency licensing disclosures
├── README.md                 # Repository documentation
├── SECURITY.md               # Vulnerability reporting security policy
├── pyproject.toml            # Build metadata configuration
├── requirements.txt          # Python dependency list
└── run.py                    # Server launch script
```

---

## 🔄 Project Workflow

1. **Document Intake**: Image uploaded via API (`/api/v1/upload/document`) or Web Chatbot (`/chat`).
2. **Quality Assessment**: `backend/services/quality_checker.py` checks blur (Laplacian variance), illumination, and angle. If quality score < threshold, rejection feedback is returned.
3. **Multilingual OCR Processing**: Document processed via Vision AI / EasyOCR engine, extracting raw text and identified language (Hindi/Marathi/English).
4. **Field Normalization & Extraction**: `field_extractor` parses key values (Farmer Name, Survey Number, Account Number, IFSC Code, Area).
5. **Database Cross-Matching**: `fuzzy_matcher` calculates similarity scores against registered database records using RapidFuzz.
6. **Fraud Analysis**: `fraud_detector` computes ELA compression differential and perceptual dhash fingerprinting to detect tampering or duplicates.
7. **Approval Routing**:
   - High confidence → **AUTO_APPROVED**
   - Medium/Low confidence → **FLAGGED FOR REVIEW** in Admin Dashboard.

---

## 🧪 Testing

Execute the automated test suite with `pytest`:

```bash
pytest tests/ -v
```

Run quick quality checking smoke test:

```bash
python test_quality_quick.py
```

---

## 🔮 Future Enhancements

- [ ] Messaging platform integration (e.g. WhatsApp / Telegram bot webhooks).
- [ ] Docker containerization (`Dockerfile` and `docker-compose.yml`).
- [ ] Offline Progressive Web App (PWA) mode for zero-connectivity field operation.
- [ ] On-device OCR model integration for low-latency offline edge processing.
- [ ] Geo-spatial land boundary verification using satellite survey maps.

---

## 📄 License

This project is open-source software licensed under the **[MIT License](LICENSE)**. Third-party dependency notice details are available in [NOTICE.md](NOTICE.md).

---

# Reporting a Vulnerability

If you discover a security vulnerability, please do not create a public GitHub issue.

Instead, email:

**kothapallisathwik5@gmail.com**

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested mitigation (if known)

I will acknowledge receipt and investigate the issue as soon as possible.

## 🤝 Contribution Guidelines

Contributions are welcome! Please follow these guidelines:
1. Fork the repository and create a feature branch (`git checkout -b feature/amazing-feature`).
2. Ensure code passes linting and unit tests (`pytest`).
3. Maintain non-proprietary, synthetic mock data in test scripts.
4. Open a Pull Request with a clear summary of changes.

---

## 🛡️ Security Note

If you discover a security vulnerability, please review our [SECURITY.md](SECURITY.md) policy and submit a responsible disclosure report to `security@example.com`. **Do not post security vulnerabilities to public issues.**

---

## 📧 Contact Information

For open-source inquiries, technical questions, or bug reports:
- **Issues**: [GitHub Issues Page](https://github.com/open-source/farmerverify-ai/issues)


---

**FarmerVerify AI** — *Empowering intelligent, accessible document processing.*
