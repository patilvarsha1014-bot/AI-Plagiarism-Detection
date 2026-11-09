# AI-Driven Plagiarism Intelligence for Assignments

> **IBM Cloud Lite / IBM Granite (watsonx.ai)** powered academic integrity system  
> Problem Statement No. 10 – Edunet Foundation

---

## 📌 Overview

An adaptive AI system that detects plagiarism, AI-generated content, and paraphrasing in student assignments by combining **IBM Granite 13B LLM analysis** with TF-IDF cosine similarity. The system learns from instructor feedback to improve accuracy over time.

---

## 🏗️ Architecture

```
plagiarism_intelligence/
├── app.py                  # Flask app factory
├── database.py             # SQLAlchemy models
├── granite_client.py       # IBM Granite (watsonx.ai) wrapper
├── analyzer.py             # Core analysis engine (TF-IDF + Granite)
├── seed_data.py            # Demo data seeder
├── requirements.txt
├── env.txt                 # ← rename to .env and fill in credentials
│
├── routes/
│   ├── assignments.py      # Course / Assignment / Submission APIs
│   ├── analysis.py         # Analysis & stats APIs
│   └── dashboard.py        # HTML page routes
│
├── templates/
│   ├── index.html          # Landing page + live stats
│   ├── submit.html         # Student submission form
│   ├── dashboard.html      # Instructor dashboard
│   └── report.html         # Full analysis report
│
├── static/
│   ├── css/style.css       # IBM Design Language stylesheet
│   └── js/app.js           # Frontend API + UI helpers
│
├── uploads/                # Uploaded files (auto-created)
└── logs/                   # Application logs (auto-created)
```

---

## ⚙️ Setup

### 1. Prerequisites
- Python 3.11+
- IBM Cloud account (free Lite tier) → [cloud.ibm.com](https://cloud.ibm.com)
- watsonx.ai project → [dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com)

### 2. Clone & install

```bash
cd plagiarism_intelligence
pip install -r requirements.txt
```

### 3. Configure environment

Rename `env.txt` → `.env` and fill in your IBM credentials:

```env
IBM_CLOUD_API_KEY=<your api key from IBM Cloud IAM>
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
IBM_WATSONX_PROJECT_ID=<your watsonx.ai project ID>
IBM_GRANITE_MODEL_ID=ibm/granite-13b-instruct-v2
SECRET_KEY=<random secret>
```

> **Without credentials** the system runs in **mock mode** — all features work with simulated Granite responses so you can develop and demo locally.

### 4. Seed demo data (optional)

```bash
python seed_data.py
```

### 5. Run

```bash
flask run
# OR
python app.py
```

Open **http://localhost:5000**

---

## 🔌 REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/assignments/courses` | List all courses |
| POST | `/api/assignments/courses` | Create course |
| GET | `/api/assignments?course_id=` | List assignments |
| POST | `/api/assignments` | Create assignment |
| GET | `/api/assignments/<id>/submissions` | List submissions with reports |
| POST | `/api/assignments/<id>/submissions` | Submit (text or file) + auto-analyze |
| POST | `/api/assignments/submissions/<id>/feedback` | Instructor feedback |
| POST | `/api/analysis/submission/<id>` | Re-analyze submission |
| GET | `/api/analysis/report/<id>` | Get report |
| POST | `/api/analysis/compare` | Compare two texts |
| GET | `/api/analysis/stats` | Global statistics |

---

## 🤖 IBM Granite Integration

The system uses **ibm/granite-13b-instruct-v2** via watsonx.ai for:

1. **Plagiarism detection** – structured JSON analysis of similarity, paraphrase probability, and verdict
2. **AI content detection** – identifies ChatGPT/AI writing patterns with evidence indicators
3. **Similarity explanation** – natural-language explanation of why two texts match

The final risk score is a **weighted ensemble**:
- TF-IDF cosine similarity: **40%**
- Granite similarity score: **35%**
- AI detection score: **25%**

Verdict thresholds (configurable in `.env`):
| Score | Verdict |
|-------|---------|
| < 0.75 | ✅ Clean |
| 0.75 – 0.80 | ⚠️ Suspicious |
| ≥ 0.80 | ❌ Flagged |

---

## 🔒 Academic Integrity Features

- **Sentence-level matching** – pinpoints exact passages copied or paraphrased
- **Cross-submission similarity** – compares against all peers in the same assignment
- **AI writing detection** – identifies ChatGPT/Gemini style patterns
- **Instructor feedback loop** – confirmed/dismissed flags improve future accuracy
- **File support** – TXT, PDF, DOCX uploads with automatic text extraction
- **Re-analysis** – instructors can trigger fresh Granite analysis at any time

---

## 🛡️ Security Notes

- Never commit `.env` to version control
- Change `SECRET_KEY` before deploying to production
- Use IBM Cloud IAM API key rotation policies
- Run behind a reverse proxy (nginx) in production

---

## 📄 License

MIT — For educational / Edunet Foundation project use.
