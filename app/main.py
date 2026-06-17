from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import user_router, route_router, report_router, barangay_router, assignment_router
from app.services import database
import os

app = FastAPI(
    title="EWAST API",
    description="Backend service for EWAST (InnovCup 2026 Entry)",
    version="1.0.0"
)

# change to file storage server in productiom
if not os.path.isdir("static"):
    os.mkdir("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# allow React app to fetch data
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/api", tags=["user"])
app.include_router(route_router, prefix="/api", tags=["route"])
app.include_router(report_router, prefix="/api", tags=["report"])
app.include_router(barangay_router, prefix="/api", tags=["barangay"])
app.include_router(assignment_router, prefix="/api", tags=["assignment"])

# replace with migration in production
@app.on_event("startup")
def on_startup():
    database.create_db_and_tables()

@app.get("/")
def root():
    return {"message": "Welcome to EWAST API"}
