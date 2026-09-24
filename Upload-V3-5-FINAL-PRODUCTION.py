"""
PetroLens v3.5 PRODUCTION - ACCURACY + NO FALLBACK + 503/426 FIX + SPINNER FIX
- Accuracy: 150k chars, 8192 tokens
- Deep = gemini-3.1-pro-preview ONLY (no fallback)
- Normal = gemini-3-flash-preview ONLY (no fallback)
- Retry: max 2 times, 15s + 30s wait for preview overload
- Returns 503 JSON (not 500) so frontend spinner stops cleanly
- Handles 404/426 model blocked for Sep 2026 keys
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import fitz
import os, re, json, time
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

load_dotenv()
router = APIRouter()

from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

MODEL_FAST = "gemini-3-flash-preview"
MODEL_DEEP = "gemini-3.1-pro-preview"

EXECUTIVE_PROMPT = """
You are a Senior Petroleum Geologist with 25 years Niger Delta deepwater experience (if the field is not in Niger Delta, then assume a senior petroleum geologist role in that field or basin), reporting to VP Exploration. You are also a strict Document Classifier.

TASK: Step 1 - CLASSIFY, Step 2 - EVALUATE ONLY IF OIL & GAS.

### STEP 1: DOCUMENT CLASSIFICATION GATE
Classify into:
A. VALID OIL & GAS GEOSCIENCE: petroleum system elements
B. INVALID / NON-OIL & GAS: Medical, legal, CV, etc.

IF B: Return JSON with is_oil_gas_document=false, commercial_viability_score 0, verdict "REJECT - NOT OIL & GAS"

### STEP 2: IF VALID OIL & GAS:
1. PETROLEUM SYSTEM CONFIDENCE 0-100 capped, prob 0.05-0.99
2. POSg = P_source × P_reservoir × P_trap × P_seal × P_charge (Rose 1987)
3. EXECUTIVE FIELDS: dominant_fluid, oil_quality, gas_quality, formation_pressure, pressure_gradient, volumetrics STOIIP/GIIP/recoverable, production_forecast initial_rate/field_life/eur

OUTPUT STRICT JSON ONLY:
{
  "is_oil_gas_document": true,
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
    text = ""
    fname = filename.lower()
    if fname.endswith(".pdf"):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
    elif fname.endswith(".docx"):
        from docx import Document
        import io
        doc = Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            text += para.text + "\n"
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text += cell.text + " "
                text += "\n"
    elif fname.endswith(".doc"):
        raise HTTPException(status_code=400, detail="Old .DOC format (binary). Please save as .DOCX or PDF and re-upload.")
    else:
        text = file_bytes.decode("utf-8", errors="ignore")
    if len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail=f"Text too short ({len(text)} chars). Scanned image PDF?")
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
        clean = re.sub(r",\s*}", "}", m.group(0))
        clean = re.sub(r",\s*]", "]", clean)
        try:
            return json.loads(clean)
        except:
            pass
    raise ValueError(f"Failed to parse JSON. Raw: {raw_text[:1000]}")

def ensure_industry_standard(data):
    if data.get("is_oil_gas_document") == False:
        return data
    petro = data.get("petroleum_system", {})
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
    return data

@router.post("/upload-report")
async def upload_report(file: UploadFile = File(...), deep: str = Form("false")):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

    file_bytes = await file.read()
    text = extract_text(file_bytes, file.filename or "report.pdf")
    prompt = EXECUTIVE_PROMPT.replace("{report_text}", text)

    is_deep = deep.lower() == "true"
    mname = MODEL_DEEP if is_deep else MODEL_FAST

    print(f"[PROD v3.5] Model={mname} Deep={is_deep} File={file.filename} Chars={len(text)}")

    max_retries = 2
    last_error = None
    raw = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[TRY {attempt}/{max_retries}] {mname} -> {file.filename}")
            resp = client.models.generate_content(
                model=mname,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=8192,
                    top_p=0.9,
                )
            )
            raw = resp.text
            print(f"[SUCCESS] {mname} attempt {attempt} returned {len(raw)} chars")
            break
        except Exception as e:
            last_error = e
            err_str = str(e)
            print(f"[FAIL {attempt}/{max_retries}] {mname} -> {err_str[:600]}")

            is_quota = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            is_overload = "503" in err_str or "overloaded" in err_str.lower() or "UNAVAILABLE" in err_str or "high demand" in err_str.lower()
            is_model_blocked = "404" in err_str or "426" in err_str or "not found" in err_str.lower() or "not supported" in err_str.lower() or "model" in err_str.lower() and "not found" in err_str.lower()

            if is_model_blocked:
                print(f"[BLOCKED] Model {mname} not available for this API key (Sep 2026 keys only allow gemini-3-*)")
                return JSONResponse(
                    status_code=404,
                    content={
                        "detail": f"Model {mname} not available for this API key. Your Sep 2026 key only supports gemini-3-flash-preview and gemini-3.1-pro-preview. You are already using the correct models. If you see this on Flash, try again - Google allowlist issue.",
                        "is_quota_error": False
                    }
                )

            if attempt == max_retries:
                print(f"[FINAL FAIL] {mname} after {max_retries} attempts")
                break

            if is_overload:
                wait = 15 if attempt == 1 else 30
                print(f"[RETRY] Preview overload, waiting {wait}s before retry {attempt+1}")
                time.sleep(wait)
                continue
            elif is_quota:
                if mname == MODEL_DEEP:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"Deep Analysis (Pro) has 0 free quota on free tier. Uncheck 'Deep Analysis' to use {MODEL_FAST} (20/day free) or add billing at https://ai.google.dev/gemini-api/docs/billing.",
                            "is_quota_error": True
                        }
                    )
                else:
                    wait = 10
                    print(f"[QUOTA] Flash quota, waiting {wait}s")
                    time.sleep(wait)
                    continue
            else:
                wait = 3
                time.sleep(wait)
                continue

    if not raw:
        err_str = str(last_error) if last_error else "Unknown"
        is_overload_final = "503" in err_str or "UNAVAILABLE" in err_str or "overloaded" in err_str.lower() or "high demand" in err_str.lower()
        
        if is_overload_final:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": f"Google preview models are currently overloaded (high demand spike, temporary 1-2 mins). Model {mname} will recover shortly. Please wait 60 seconds and click Generate again. No quota used.",
                    "is_quota_error": False
                }
            )
        
        if "429" in err_str or "quota" in err_str.lower():
            if mname == MODEL_DEEP:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Deep Analysis quota exceeded. Pro model ({MODEL_DEEP}) has 0 free quota. Uncheck Deep Analysis for Flash (20/day free).",
                        "is_quota_error": True
                    }
                )
            else:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Daily quota exceeded (20/day on {MODEL_FAST}). Retried {max_retries} times. Wait 60s or try tomorrow 8am Lagos.",
                        "is_quota_error": True
                    }
                )
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"AI service failed after {max_retries} retries: {err_str[:800]}",
                "is_quota_error": False
            }
        )

    if not raw or len(raw.strip()) < 10:
        raise HTTPException(status_code=500, detail=f"Gemini empty response for {mname}")

    try:
        analysis = parse_gemini_json(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JSON parse failed: {e} | Raw: {raw[:2000]}")

    analysis = ensure_industry_standard(analysis)
    return {"analysis": analysis, "filename": file.filename, "model_used": mname}
