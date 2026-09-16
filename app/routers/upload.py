from fastapi import APIRouter, UploadFile, File, HTTPException
import pymupdf as fitz
from app.services.llm_parser import parse_geoscience_report

router = APIRouter()

@router.post("/upload-report")
async def upload_report(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF allowed")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Max 10MB")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = "".join([page.get_text() + "\n" for page in doc])
        page_count = len(doc)
        doc.close()
        if len(full_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Scanned PDF - no extractable text")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF read failed: {e}")

    result = await parse_geoscience_report(full_text)
    
    return {
        "filename": file.filename,
        "pages": page_count,
        "characters_extracted": len(full_text),
        "analysis": result["analysis"] # This now matches your frontend gauge
    }