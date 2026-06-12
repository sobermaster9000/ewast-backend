from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import citizen_router, admin_router, collector_router

app = FastAPI(
    title="EWAST API",
    description="Backend service for EWAST (InnovCup 2026 Entry)",
    version="1.0.0"
)

# allow React app to fetch data
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(citizen_router, prefix="/api", tags=["citizen"])
app.include_router(admin_router, prefix="/api", tags=["admin"])
app.include_router(collector_router, prefix="/api", tags=["collector"])

@app.get("/")
def root():
    return {"message": "Welcome to EWAST API"}
