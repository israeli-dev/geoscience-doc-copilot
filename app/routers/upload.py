"""
PetroLens FIXED for Sep 2026 Gemini API keys
- Only models allowed: gemini-3-flash-preview (FREE quota) and gemini-3.1-pro-preview (which is 0 quota on free tier)
- Fix: Use Flash as PRIMARY, Pro as fallback only when Deep=True
- Fix: Return 429 JSON not 500, so Streamlit shows retry message
- Fix: Proper DOCX support
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import fitz
import os, re, json, time, traceback
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

from google import genai
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
        raise HTTPException(400, "Old .DOC format (binary). Please save as .DOCX or PDF and re-upload.")
    else:
        text = file_bytes.decode("utf-8", errors="ignore")
    if len(text.strip()) < 20:
        raise HTTPException(400, f"Text too short ({len(text)} chars). Scanned image PDF?")
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

def try_chat_api(mname, prmpt):
    from google.genai import types
    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=8192,
        top_p=0.9,
    )
    try:
        chat = client.chats.create(model=mname, config=config)
        resp = chat.send_message(prmpt)
        return resp.text
    except Exception as e:
        # Fallback to models.generate_content
        try:
            resp = client.models.generate_content(model=mname, contents=prmpt, config=config)
            return resp.text
        except Exception as e2:
            raise e2

@router.post("/upload-report")
async def upload_report(file: UploadFile = File(...), deep: str = Form("false")):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not set")

    file_bytes = await file.read()
    text = extract_text(file_bytes, file.filename or "report.pdf")
    prompt = EXECUTIVE_PROMPT.replace("{report_text}", text)

    # SEP 2026 FIX: Flash is primary (has free quota), Pro needs payment: has 0 quota on free tier
    # If deep=True, try Pro first then Flash fallback
    # If deep=False, use Flash only (avoid Pro 429)
    is_deep = deep.lower() == "true"
    models_to_try = [MODEL_DEEP, MODEL_FAST] if is_deep else [MODEL_FAST]

    raw = ""
    last_error = None
    model_used_final = MODEL_FAST

    for mname in models_to_try:
        try:
            print(f"[TRY] {mname} for file {file.filename} deep={is_deep}")
            raw = try_chat_api(mname, prompt)
            model_used_final = mname
            print(f"[SUCCESS] {mname} returned {len(raw)} chars")
            break
        except Exception as e:
            last_error = e
            print(f"[FAIL] {mname} -> {e}")
            print(traceback.format_exc())
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                # If Pro failed with 429 and we have Flash fallback, try next model
                if mname == MODEL_DEEP and MODEL_FAST in models_to_try or mname == MODEL_DEEP:
                    # If deep was true, now try flash as fallback
                    if MODEL_FAST not in models_to_try:
                        models_to_try.append(MODEL_FAST)
                    print(f"[WARN] Pro {MODEL_DEEP} quota 0, falling back to {MODEL_FAST}")
                    continue
                # If Flash also 429, wait and retry once
                if mname == MODEL_FAST:
                    print("[QUOTA] Flash also hit 429, sleeping 10s then retry once")
                    time.sleep(10)
                    try:
                        raw = try_chat_api(mname, prompt)
                        model_used_final = mname
                        break
                    except Exception as e2:
                        last_error = e2
                        continue
            # For other errors, try next model
            continue

    if not raw:
        # Both failed - return mock data to avoid 500, but log error
        print(f"[CRITICAL] Both models failed. Last error: {last_error}")
        # Return 429 JSON so frontend shows friendly message
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Gemini quota exceeded (Sep 2026 free tier limit 0 for Pro). Last: {str(last_error)[:500]}. Please wait 1 min and uncheck Deep Analysis checkbox, or add billing at https://ai.google.dev/gemini-api/docs/billing. Tip: Use Flash model (Deep unchecked) which has free quota.",
                "is_quota_error": True
            }
        )

    if not raw or len(raw.strip()) < 10:
        raise HTTPException(500, f"Gemini empty response for {model_used_final}")

    try:
        analysis = parse_gemini_json(raw)
    except Exception as e:
        raise HTTPException(500, f"JSON parse failed: {e} | Raw: {raw[:2000]}")

    analysis = ensure_industry_standard(analysis)
    return {"analysis": analysis, "filename": file.filename, "model_used": model_used_final}
