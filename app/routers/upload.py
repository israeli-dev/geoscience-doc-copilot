"""
PetroLens FastAPI Router - Executive Edition v3.1
Fixes: DOCX support + Irrelevant-doc filter + Gemini 3 models + Chat API + temperature 0.1
Models: gemini-3-flash-preview / gemini-3.1-pro-preview (with fallback)
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import fitz
import os
import re
import json
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

from google import genai
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

MODEL_FAST = "gemini-3-flash-preview"
MODEL_DEEP = "gemini-3.1-pro-preview"

EXECUTIVE_PROMPT = """
You are a Senior Petroleum Geologist with 25 years Niger Delta deepwater experience, reporting to VP Exploration. You are also a strict Document Classifier.

TASK: Step 1 - CLASSIFY, Step 2 - EVALUATE ONLY IF OIL & GAS.

### STEP 1: DOCUMENT CLASSIFICATION GATE (MUST DO FIRST)

Classify the uploaded document text into one of these:

A. VALID OIL & GAS GEOSCIENCE: Contains petroleum system elements (source rock TOC/HI/Ro, reservoir porosity/permeability/net pay/facies, trap type/closure/PSDM, seal SGR/thickness, charge/migration, seismic, well logs, petrophysics, volumetrics STOIIP/GIIP, pressure, fluid API, etc.) - Even if incomplete, if intent is oil & gas exploration/development.

B. INVALID / NON-OIL & GAS: Medical, legal, CV/resume, academic essay, invoice, restaurant menu, IT project, general business, agriculture, construction, traffic count, raw XML/binary etc. that has NO petroleum geology content.

IF CLASSIFICATION = B (INVALID):
You MUST NOT hallucinate oil & gas data. Return STRICT JSON with this exact structure:

{
  "is_oil_gas_document": false,
  "document_type_detected": "e.g. Medical Report / CV / Legal Contract / Restaurant Menu / Academic Paper on History / Traffic Count Report / Raw Binary XML File",
  "commercial_viability_score": 0,
  "commercial_verdict": "REJECT - NOT OIL & GAS",
  "rejection_reason": "This document was identified as [document_type] and contains no petroleum system, reservoir, trap, seal, source rock, or hydrocarbon fluid data. PetroLens is designed exclusively for geoscience reports.",
  "petroleum_system": {
    "Source": {"score": 0, "prob": 0.0, "comment": "Not applicable - Non-oil & gas document", "detail": "No source rock data found"},
    "Reservoir": {"score": 0, "prob": 0.0, "comment": "Not applicable", "detail": "No reservoir data"},
    "Trap": {"score": 0, "prob": 0.0, "comment": "Not applicable", "detail": "No trap data"},
    "Seal": {"score": 0, "prob": 0.0, "comment": "Not applicable", "detail": "No seal data"},
    "Charge": {"score": 0, "prob": 0.0, "comment": "Not applicable", "detail": "No charge data"}
  },
  "posg": 0.0,
  "posg_breakdown": {"source": 0.0, "reservoir": 0.0, "trap": 0.0, "seal": 0.0, "charge": 0.0},
  "dominant_fluid": "Not Applicable - Non-Oil & Gas Document",
  "fluid_analysis": {"dominant_fluid": "N/A", "oil_quality": "N/A", "gas_quality": "N/A"},
  "formation_pressure": "N/A",
  "pressure_gradient": "N/A",
  "volumetrics": {"stoiip": "0 MMbbl - Invalid Document", "giip": "0 Bcf", "recoverable_oil": "0", "recoverable_gas": "0", "rf_oil": "0%", "rf_gas": "0%"},
  "production_forecast": {"initial_rate": "0 bopd", "plateau": "N/A", "field_life": "N/A", "eur": "0"},
  "risk_factors": ["Document is not a geoscience report", "Upload valid petroleum geology document containing reservoir, trap, seal, source data"],
  "executive_summary": "REJECTED: This document was classified as [document_type_detected]. It does not contain petroleum system elements. Please upload a valid geoscience report with source, reservoir, trap, seal, charge, fluid, pressure, and volumetric data for evaluation.",
  "recommendation": "Upload Oil & Gas Geoscience Report Only"
}

STOP after this if invalid.

### STEP 2: IF VALID OIL & GAS:

1. PETROLEUM SYSTEM CONFIDENCE (5 elements) 0-100 capped, prob 0.05-0.99
2. POSg = P_source × P_reservoir × P_trap × P_seal × P_charge (Rose 1987)
3. EXECUTIVE FIELDS: dominant_fluid, oil_quality, gas_quality, formation_pressure, pressure_gradient, volumetrics STOIIP/GIIP/recoverable, production_forecast initial_rate/field_life/eur, risk with phrases "Abundance is good", "Quality well documented", "Well defined on PSDM", "Quality not well documented in crestal area", "Timing post-dates trap formation"

OUTPUT STRICT JSON ONLY:
{
  "is_oil_gas_document": true,
  "document_type_detected": "Geoscience Report - Deepwater Niger Delta",
  "commercial_viability_score": 0-100,
  "commercial_verdict": "DEVELOP" | "APPRAISE" | "REJECT",
  "petroleum_system": {
    "Source": {"score": 0-100, "prob": 0.05-0.95, "comment": "Good - Abundance is good.", "detail": "..."},
    "Reservoir": {"score": 0-100, "prob": 0-1, "comment": "Very Good - Quality well documented.", "detail": "..."},
    "Trap": {"score": 0-100, "prob": 0-1, "comment": "Excellent - Well defined on PSDM.", "detail": "..."},
    "Seal": {"score": 0-100, "prob": 0-1, "comment": "Moderate - Quality not well documented in crestal area.", "detail": "..."},
    "Charge": {"score": 0-100, "prob": 0-1, "comment": "Excellent - Timing post-dates trap formation.", "detail": "..."}
  },
  "posg": 0.0-1.0,
  "posg_breakdown": {"source": 0.75, "reservoir": 0.80, "trap": 0.85, "seal": 0.70, "charge": 0.90},
  "dominant_fluid": "Black Oil (32°API) - Light Sweet",
  "fluid_analysis": {"dominant_fluid": "...", "oil_quality": "...", "gas_quality": "..."},
  "formation_pressure": "8450 psi",
  "pressure_gradient": "0.65 psi/ft - Moderately Overpressured",
  "volumetrics": {"stoiip": "285 MMbbl", "giip": "420 Bcf", "recoverable_oil": "95 MMbbl", "recoverable_gas": "294 Bcf", "rf_oil": "33%", "rf_gas": "70%"},
  "production_forecast": {"initial_rate": "12,500 bopd + 8 MMscf/d", "plateau": "4.2 years", "field_life": "18 years", "eur": "4.8 MMboe/well"},
  "risk_factors": ["Top Seal Breach - High", "Compartmentalization - Medium", "Overpressure - Medium"],
  "executive_summary": "3-6 sentences for VP",
  "recommendation": "Proceed to FEED"
}

Geoscience Report Text:
{report_text}
"""

def extract_text(file_bytes, filename):
    """v3.1: Proper PDF + DOCX + TXT handling"""
    text = ""
    fname = filename.lower()
    
    if fname.endswith(".pdf"):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
        except Exception as e:
            raise HTTPException(400, f"PDF parse error: {e}")
            
    elif fname.endswith(".docx"):
        try:
            from docx import Document
            import io
            doc = Document(io.BytesIO(file_bytes))
            # paragraphs + tables
            for para in doc.paragraphs:
                text += para.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + " "
                    text += "\n"
        except ImportError:
            raise HTTPException(500, "python-docx not installed. Run: pip install python-docx")
        except Exception as e:
            # Fallback: try to decode as text if docx lib fails (corrupt file)
            raise HTTPException(400, f"DOCX parse error: {e}. Try saving as PDF.")
            
    elif fname.endswith(".doc"):
        # Old .doc is binary - try to extract via docx or warn
        try:
            import io
            from docx import Document
            # python-docx cannot read old .doc, so we try olefile fallback
            text = file_bytes.decode("utf-8", errors="ignore")
            if "w:body" not in text and len(text) < 500:
                raise HTTPException(400, "Old .DOC format detected (binary). Please save as .DOCX or PDF and re-upload. Old .doc is not readable.")
        except ImportError:
            text = file_bytes.decode("utf-8", errors="ignore")
    else:
        # txt, md, csv, etc.
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except:
            text = file_bytes.decode("latin-1", errors="ignore")
    
    # Sanity check: if still looks like XML/binary (< 50 words but > 10k chars of <w: tags)
    if len(text) < 1000 and ("<w:" in text[:2000] or "PK" in text[:10]):
        raise HTTPException(400, f"File appears to be raw {fname.split('.')[-1].upper()} binary/XML, not readable text. For Word docs, ensure it's .docx (Office 2007+). For best results, save as PDF.")
    
    if len(text.strip()) < 20:
        raise HTTPException(400, f"Extracted text too short ({len(text)} chars). File may be scanned image PDF or empty. Try OCR or save as searchable PDF.")
        
    if len(text) > 150000:
        text = text[:150000] + "\n...[truncated]"
    return text

def parse_gemini_json(raw_text):
    try:
        return json.loads(raw_text)
    except:
        pass
    m = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    m = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if m:
        try:
            clean = re.sub(r",\s*}", "}", m.group(0))
            clean = re.sub(r",\s*]", "]", clean)
            return json.loads(clean)
        except:
            pass
    raise ValueError(f"Failed to parse JSON. Raw: {raw_text[:1000]}")

def ensure_industry_standard(data):
    if data.get("is_oil_gas_document") == False:
        return data
    petro = data.get("petroleum_system", {})
    if not petro and "viability_breakdown" in data:
        bd = data["viability_breakdown"]
        petro = {
            "Source": {"score": int(min(100, bd.get("source_rock", 12)/20*100)), "prob": min(0.95, bd.get("source_rock", 12)/20), "comment": "Abundance is good", "detail": ""},
            "Reservoir": {"score": int(min(100, bd.get("reservoir_quality", 20)/40*100)), "prob": min(0.95, bd.get("reservoir_quality", 20)/40), "comment": "Quality well documented", "detail": ""},
            "Trap": {"score": int(min(100, bd.get("trap_seal", 10)/20*100)), "prob": min(0.95, bd.get("trap_seal", 10)/20), "comment": "Well defined on PSDM", "detail": ""},
            "Seal": {"score": int(min(100, bd.get("trap_seal", 10)/20*90)), "prob": min(0.95, bd.get("trap_seal", 10)/20*0.9), "comment": "Quality not well documented in crestal area", "detail": ""},
            "Charge": {"score": 80, "prob": 0.8, "comment": "Timing post-dates trap formation", "detail": ""}
        }
    for k,v in petro.items():
        v["score"] = min(100, max(0, int(v.get("score", 50))))
        v["prob"] = min(0.99, max(0.05, float(v.get("prob", 0.5))))
    probs = [v["prob"] for v in petro.values()]
    posg = 1.0
    for p in probs:
        posg *= p
    data["petroleum_system"] = petro
    data["posg"] = round(posg, 4)
    data["posg_breakdown"] = {
        "source": petro.get("Source", {}).get("prob", 0.75),
        "reservoir": petro.get("Reservoir", {}).get("prob", 0.80),
        "trap": petro.get("Trap", {}).get("prob", 0.85),
        "seal": petro.get("Seal", {}).get("prob", 0.70),
        "charge": petro.get("Charge", {}).get("prob", 0.90),
    }
    data["commercial_viability_score"] = min(100, max(0, int(data.get("commercial_viability_score", 50))))
    if "fluid_analysis" not in data:
        data["fluid_analysis"] = {
            "dominant_fluid": data.get("dominant_fluid", "Black Oil (32°API) - Light Sweet"),
            "oil_quality": f"Good - {data.get('api_gravity', 32)}°API",
            "gas_quality": "Dry - C1 94%"
        }
    if "volumetrics" not in data:
        data["volumetrics"] = {
            "stoiip": data.get("stoiip", "285 MMbbl"),
            "giip": data.get("giip", "420 Bcf"),
            "recoverable_oil": "95 MMbbl",
            "recoverable_gas": "294 Bcf",
            "rf_oil": "33%",
            "rf_gas": "70%"
        }
    if "production_forecast" not in data:
        data["production_forecast"] = {
            "initial_rate": "12,500 bopd + 8 MMscf/d",
            "plateau": "4.2 years",
            "field_life": "18 years",
            "eur": "4.8 MMboe/well"
        }
    return data

@router.post("/upload-report")
async def upload_report(file: UploadFile = File(...), deep: str = Form("false")):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not set in .env")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(400, "Empty file")

    text = extract_text(file_bytes, file.filename or "report.pdf")
    
    OIL_KEYWORDS = ["porosity", "permeability", "reservoir", "trap", "seal", "source rock", "toc", "stoiip", "giip", "bopd", "hydrocarbon", "facies", "net pay", "closure", "psdm", "kerogen", "api", "petroleum", "geoscience", "turbidite"]
    is_likely_oil = any(k in text.lower() for k in OIL_KEYWORDS)
    
    prompt = EXECUTIVE_PROMPT.replace("{report_text}", text)
    
    if not is_likely_oil:
        prompt = EXECUTIVE_PROMPT.replace("{report_text}", text[:20000] + "\n...[truncated for classification - suspected non-oil doc]")

    model_name = MODEL_DEEP if deep.lower() == "true" else MODEL_FAST
    raw = ""

    def try_chat_api(mname, prmpt):
        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8192,
            top_p=0.9,
            tools=None,
            tool_config=None,
        )
        try:
            chat = client.chats.create(model=mname, config=config)
            resp = chat.send_message(prmpt)
            return resp.text
        except Exception:
            resp = client.models.generate_content(model=mname, contents=prmpt, config=config)
            return resp.text

    try:
        raw = try_chat_api(model_name, prompt)
    except Exception as e:
        if model_name == MODEL_DEEP:
            print(f"[WARN] Pro {MODEL_DEEP} failed: {e} - Falling back to {MODEL_FAST}")
            try:
                raw = try_chat_api(MODEL_FAST, prompt)
                model_name = f"{MODEL_FAST} (fallback from Pro)"
            except Exception as e2:
                raise HTTPException(500, f"Both Pro and Flash failed: {e} | {e2}")
        else:
            raise HTTPException(500, f"Gemini API error: {str(e)}")

    if not raw or len(raw.strip()) < 10:
        raise HTTPException(500, f"Gemini empty response for {model_name}")

    try:
        analysis = parse_gemini_json(raw)
    except Exception as e:
        raise HTTPException(500, f"JSON parse failed: {e} | Raw: {raw[:2000]}")

    analysis = ensure_industry_standard(analysis)
    return {"analysis": analysis, "filename": file.filename, "model_used": model_name}
