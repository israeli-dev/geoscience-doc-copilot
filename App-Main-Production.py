from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import upload, analytics
import os

app = FastAPI(
    title="PetroLens Production v3.5",
    description="Petroleum System & Commercial Viability - Production",
    version="3.5.0"
)

# CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])

@app.get("/")
def root():
    return {"status": "PetroLens Active", "version": "v3.5 Production", "models": ["gemini-3-flash-preview", "gemini-3.1-pro-preview"]}

@app.get("/health")
def health():
    return {"status": "ok"}
