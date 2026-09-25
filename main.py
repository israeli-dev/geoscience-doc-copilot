from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import upload

# Try to import analytics if exists, else ignore
try:
    from app.routers import analytics
    HAS_ANALYTICS = True
except ImportError:
    analytics = None
    HAS_ANALYTICS = False

app = FastAPI(title="PetroLens Executive API Production v3.5", version="3.5 Production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")

if HAS_ANALYTICS and analytics:
    app.include_router(analytics.router, prefix="/api")

@app.get("/")
def root():
    return {"status": "PetroLens Active", "version": "v3.5 Production", "docs": "/docs", "analytics": HAS_ANALYTICS}

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.5"}
