import os
import json
from dotenv import load_dotenv
from google import genai
import re

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
You are a Senior Petroleum Geologist. Evaluate commercial viability.
You MUST return ONLY valid JSON with this exact schema, no markdown:

{
  "commercial_viability_score": 0-100,
  "commercial_verdict": "DEVELOP or APPRAISE or REJECT",
  "viability_breakdown": {
    "reservoir_quality": 0-40,
    "source_rock": 0-20,
    "trap_seal": 0-20,
    "commercial_risk": 0-20
  },
  "reservoir_quality": {"porosity": "e.g. 22%", "permeability": "e.g. 150mD", "net_pay": "e.g. 15m"},
  "source_rock": {"TOC": "e.g. 2.1%", "maturity": "e.g. Ro 0.9%"},
  "trap": {"type": "e.g. rollover anticline", "seal": "e.g. Agbada shale"},
  "risk_factors": ["Risk 1", "Risk 2", "Risk 3"],
  "executive_summary": "2 sentence blunt commercial verdict",
  "AFC_flag": "Low/Med/High"
}
"""

async def parse_geoscience_report(full_text: str, deep: bool = False):
    model = "gemini-3.1-pro-preview" if deep else "gemini-3-flash-preview"
    prompt = f"{SYSTEM_PROMPT}\n\nREPORT:\n{full_text[:80000]}\n\nReturn JSON only."
    
    chat = client.chats.create(model=model)
    resp = chat.send_message(prompt)
    
    # Clean markdown ```json fences if Gemini adds them
    clean_text = re.sub(r'```json|```', '', resp.text).strip()
    
    try:
        data = json.loads(clean_text)
    except:
        # Fallback if Gemini returns text: extract score manually
        score_match = re.search(r'(\d+)/100', resp.text)
        score = int(score_match.group(1)) if score_match else 45
        data = {
            "commercial_viability_score": score,
            "commercial_verdict": "APPRAISE" if score>=50 else "REJECT",
            "viability_breakdown": {"reservoir_quality": 20, "source_rock": 10, "trap_seal": 10, "commercial_risk": 5},
            "reservoir_quality": {"porosity": "N/A", "permeability": "N/A", "net_pay": "N/A"},
            "source_rock": {"TOC": "N/A", "maturity": "N/A"},
            "trap": {"type": "N/A", "seal": "N/A"},
            "risk_factors": ["Could not parse structured data"],
            "executive_summary": resp.text[:500],
            "AFC_flag": "Med"
        }
    return {"model": model, "analysis": data, "raw_text": resp.text}