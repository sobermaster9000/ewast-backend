from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import user_router, route_router, report_router, barangay_router, assignment_router
from app.services import database
from app.config import settings
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION
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

@app.on_event("startup")
def on_startup():
    database.init_barangays_table()

@app.get("/")
def root():
    return {"detail": f"Welcome to {settings.PROJECT_NAME}. {settings.DESCRIPTION}. Version {settings.VERSION}"}
