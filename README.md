# PetroLens AI - Geoscience Doc Copilot

> **Upload a petroleum geoscience report (PDF) → Get a commercial viability verdict in < 5 seconds.**
> Blunt, investor-grade analysis: DEVELOP / APPRAISE / REJECT.

[Python](https://img.shields.io/badge/Python-3.14-blue)
[FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
[Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red)
[Gemini](https://img.shields.io/badge/Gemini-3_Flash_%2F_Pro-orange)

Live Backend Docs: `http://127.0.0.1:8001/docs` (local) | Live Frontend: `http://localhost:8501`

### Why This Exists (The Problem)

Petroleum geologists waste 3-6 hours manually reading 40-80 page well reports, G&G evaluations, and play assessments to answer one question: **Is this drillable / commercial?**

Most AI PDF tools summarize. They don't *evaluate*. They don't tell you porosity is trash or seal is high-risk.

### What It Does (The Solution)

PetroLens is a **domain-specific copilot** that acts like a Senior Petroleum Geologist. It doesn't summarize - it **scores commercial viability**.

Input: Any PDF (well completion report, reservoir evaluation, source rock study, seismic interpretation)
Output:
- **Commercial Viability Score: 0-100** with animated gauge
- **Verdict: DEVELOP / APPRAISE / REJECT**
- **Breakdown:** Reservoir Quality (0-40), Source Rock (0-20), Trap/Seal (0-20), Commercial Risk (0-20)
- **Parsed Parameters:** Porosity, Permeability, Net Pay, TOC, Ro%, Trap type, Seal
- **Risk Factors & Executive Summary**
- **AFC Flag:** Low/Med/High (Above Field Commerciality)

### Demo

[Architecture](https://via.placeholder.com/800x400?text=Add+your+Streamlit+Screenshot+Here)

**Flow:** User uploads PDF on Streamlit → FastAPI extracts text with PyMuPDF → Gemini 3 Flash (fast) or Pro (deep) parses with strict JSON schema → Streamlit renders gauge with Plotly.

### Key Features for v1 (Petroleum-Specialized)

- [x] **Petroleum-only System Prompt** - No generic summarizer. Understands Niger Delta, Agbada/Akata, rollover anticlines, 4-way closures.
- [x] **Dual Model Strategy:** `gemini-3-flash-preview` for speed, `gemini-3.1-pro-preview` for deep evaluation
- [x] **Strict JSON Enforcement** with fallback regex parsing (handles LLM markdown leaks)
- [x] **Full-Stack:** FastAPI backend (`/api/upload-report`) + Streamlit frontend with `st.plotly_chart` gauge
- [x] **Production-ready structure:** `app/services/`, `app/routers/`, `app/schemas/`, `frontend/`, `tests/`

### Tech Stack

**Backend:** FastAPI, Uvicorn, PyMuPDF (pdf extraction), Pydantic, python-multipart
**AI:** Google GenAI SDK, Gemini 3 Flash / Pro, Dotenv for key management
**Frontend:** Streamlit, Plotly (gauge chart), Requests
**Dev:** Python 3.14, venv, pytest

### Project Structure

```
geoscience-doc-copilot/
├── main.py                     # FastAPI entry (at ROOT - important!)
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── services/
│   │   └── llm_parser.py       # The brain - petroleum prompt + Gemini call
│   ├── routers/
│   │   └── upload.py           # /api/upload-report endpoint
│   └── schemas/
├── frontend/
│   └── streamlit_app.py        # Gauge UI
├── tests/
├── .env                        # GEMINI_API_KEY=...
├── requirements.txt
└── README.md
```

### How to Run Locally (The Fix That Took 2 Hours)

The gotcha: `main.py` MUST be at root, not inside `app/`. And import must be `from app.services.llm_parser import ...` not `from app.llm_parser import ...`.

**1. Clone & Setup**
```powershell
git clone https://github.com/<israeli-dev>/geoscience-doc-copilot.git
cd geoscience-doc-copilot
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**2. Env**
Create `.env`:
```
GEMINI_API_KEY=your_key_here
```

**3. Run Backend (Terminal 1) - Use 0.0.0.0 and 8001 to avoid Windows firewall/reload bug**
```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8001
# Docs: http://127.0.0.1:8001/docs
```

**4. Run Frontend (Terminal 2)**
```powershell
.\venv\Scripts\Activate.ps1
# Ensure frontend/streamlit_app.py has: BACKEND_URL = "http://127.0.0.1:8001/api/upload-report"
streamlit run frontend/streamlit_app.py --server.port 8501
# App: http://localhost:8501
```

### Example API Response

```json
{
  "model": "gemini-3-flash-preview",
  "analysis": {
    "commercial_viability_score": 73,
    "commercial_verdict": "APPRAISE",
    "viability_breakdown": {
      "reservoir_quality": 32,
      "source_rock": 15,
      "trap_seal": 16,
      "commercial_risk": 10
    },
    "reservoir_quality": {"porosity": "22%", "permeability": "150mD", "net_pay": "15m"},
    "risk_factors": ["High water cut risk", "Fault seal uncertainty"],
    "executive_summary": "Good reservoir, moderate source maturity. Needs appraisal well to de-risk trap.",
    "AFC_flag": "Med"
  }
}
```

### Roadmap

**v1 (Current): Petroleum Specialist** - DELIBERATELY NICHE for portfolio positioning. Proves domain expertise.
**v2:** Add groundwater / water resources mode (separate prompt + toggle in UI)
**v3:** Deploy: Backend to Render, Frontend to Streamlit Cloud, add auth + report history DB
**v4:** Add map view for trap location, cross-section Q&A

### Why Petroleum Specialized (Design Decision)

I tested with a water resources report and it worked, but I chose to keep v1(first-version) petroleum-specific/tuned. Generic RAG = commodity, while specialised application = tool. This version is equiped with a cool feature like petroleum **viability scorer**, a big deal and a time saver for industry folks, valuable tool for Subsurface, and Oil & Gas analytics. 

---
Built by Kolawole, Israel Iyanu | Geoscientist turned AI Engineer.
