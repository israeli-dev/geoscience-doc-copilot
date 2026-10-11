# PetroLens Executive v3.5 — Subsurface Intelligence Platform

> **Upload a petroleum geoscience report (PDF/DOCX/TXT/MD) → Get Commercial Viability + POSg + Executive PDF in <30s.**

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B)](https://streamlit.io/)
[![Gemini](https://img.shields.io/badge/AI-Gemini_3_Flash%2FPro-8E44AD)](https://ai.google.dev/)
[![Live](https://img.shields.io/badge/Live-Production-brightgreen)]()

**Live App:** https://geoscience-doc-copilot-5t3ani8cv8yuuqmqtgzhaq.streamlit.app/
**API:** https://geoscience-doc-copilot-1.onrender.com/ | **Docs:** https://geoscience-doc-copilot-1.onrender.com/docs

---

### 1. The Problem

Petroleum Geologists and Reservoir Engineers waste **3-6 hours** manually reading **40-80 page well reports, field studies, and lab data** to answer one question:

> **Is this prospect drillable / commercial?**

Generic AI PDF summarizers fail because:
1. They summarize, they don't **evaluate** like a Senior Geologist
2. They give high scores to ANY reservoir report (even a civil water dam)
3. They don't calculate **POSg (Chance of Success)** or **STOIIP/Recoverable**
4. They have no investor-grade verdict: **DEVELOP / APPRAISE / REJECT**

**PetroLens solves this.** It's a domain-specific copilot that acts like a Senior Petroleum Geologist, not a summarizer.

### 2. Technologies Used

**Frontend - Executive Dashboard**
- **Streamlit** — Public web UI, mobile responsive
- **Plotly (graph_objects)** — POSg Gauge, Viability Gauge, Petroleum System Bar Chart
- **ReportLab** — Executive PDF Export (A4 investor report)

**Backend - Subsurface Intelligence Engine**
- **FastAPI** — REST API (`POST /api/upload-report`)
- **Uvicorn + Docker** — Production server on Render
- **Pydantic** — Request validation & strict JSON response

**AI Core**
- **Google Gemini 3 Flash** — Standard Mode (speed, 1.5k req/day)
- **Google Gemini 3 Pro** — Deep Analysis Mode (depth, 50 req/day)
- **Custom Petroleum Prompt** — Niger Delta, Agbada/Akata, Wrench Fault Blocks, Source Rock maturity (TOC, Ro%)

**Infrastructure & DevOps**
- **Render (Docker Web Service)** — Backend hosting `geoscience-doc-copilot-1.onrender.com`
- **Streamlit Community Cloud** — Frontend hosting
- **UptimeRobot** — 5-min HTTP ping on both frontend & backend (100% uptime, fixes sleep issue)

**Core Logic (Python)**
- POSg = Source × Reservoir × Trap × Seal × Charge (Rose 1987 Multiplicative)
- Commercial Viability Score 0-100 + AFC Flag (Low/Med/High)
- Fluid & Volumetrics Parser (API, GOR, Pressure Gradient)

### 3. Implemented Features (v3.5 Production)

**A. Analysis Engine**
- [x] Click-to-analyze (analyzes ONLY when user clicks "Analyze" — saves quota)
- [x] Dual Model Selection: `model=flash | pro`
- [x] No auto-retry on failure (saves Gemini quota)
- [x] Non-petroleum rejection — If doc is not Oil & Gas → `REJECT - Not Oil & Gas Document`
- [x] Supports PDF, DOCX, TXT, MD (200MB limit)

**B. Dual Gauge Evaluation**
- [x] **POSg Gauge** (0-100%) — Geological chance of success
- [x] **Viability Gauge** (0-100) — Commercial score

**C. Petroleum System Breakdown (100 per element)**
- [x] Source, Reservoir, Trap, Seal, Charge — each with Score, Prob, Comment
- [x] Bar chart visualization with confidence

**D. Fluid, Formation & Production**
- [x] Dominant Fluid, Oil Quality (API), Gas Quality
- [x] Pressure & Gradient, Net Pay, Porosity, Permeability
- [x] Volumetrics: STOIIP, Recoverable Oil/Gas
- [x] Production Forecast: Initial Rate, Plateau, Field Life

**E. Executive Outputs**
- [x] Verdict: DEVELOP / APPRAISE / REJECT
- [x] AFC Flag (Appraise-Flag-Check): Low/Med/High Risk
- [x] Executive Summary (investor-grade 3-4 lines)
- [x] Risk Factors List (1..n)
- [x] Downloadable Executive Report PDF (ReportLab A4)

**F. Public Access**
- [x] No login required — public link works on phone (Chrome/Safari)
- [x] Wakeup endpoint separate from analysis (`GET /` ping)

### 4. Demo — Real Reports Tested

| Report Type | Pages | POSg | Viability | Verdict | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NigerDelta Field Report** | 58 | 42% | 68 | APPRAISE | Correct |
| **Petroleum Province (Albian)** | 39 | 55% | 72 | APPRAISE | 25% Porosity, 200mD |
| **Civil Water Reservoir** | 133 | 8% | 12 | REJECT | Correctly filtered |

> Generic RAG would score both 70+. PetroLens correctly rejects non-petroleum.

### 5. Setup Instructions

#### Prerequisites
- Python 3.11+
- Gemini API Key from https://aistudio.google.com/

#### Local Setup

```bash
# 1. Clone
git clone https://github.com/israeli-dev/geoscience-doc-copilot.git
cd geoscience-doc-copilot

# 2. Create venv
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements_backend.txt

# 4. Create.env file
# Create a file named.env in root and add:
GEMINI_API_KEY=your_gemini_api_key_here

# 5. Run Backend (Terminal 1)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 6. Run Frontend (Terminal 2)
streamlit run frontend/streamlit_app.py --server.port 8501

# Open:
# Backend Docs -> http://localhost:8001/docs
# Frontend App -> http://localhost:8501

#### Docker Setup
docker build -t petrolens.
docker run -p 8001:8001 --env-file.env petrolens

#### Environment Variables (.env.example):
GEMINI_API_KEY=AIzaSy...

#### Architecture

[User Upload]
  -> Streamlit Cloud (8501)
    -> POST /api/upload-report + model param to Render FastAPI (Docker)
      -> PyMuPDF Parser -> Gemini 3 Flash/Pro -> Strict JSON
        -> POSg Calculation (Python) -> Plotly Gauges + PDF

#### Roadmap
v1: Petroleum Specialist[x]
v2: Dual model + water rejection[x]
v3: POSg + Fluid + PDF[x]
v3.5: Public + UptimeRobot + Click-to-analyze[x]
 v4: Map view + Interactive STOIIP Calculator + Shareable Links