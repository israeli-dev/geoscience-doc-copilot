from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import upload, analytics

app = FastAPI(title="PetroLens Executive API Production v3.5", version="3.5 Production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

@app.get("/")
def root():
    return {"status": "PetroLens Active", "version": "v3.5 Production", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.5"}
