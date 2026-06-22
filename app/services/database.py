from pathlib import Path
import json

from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, select

from app.schemas import Barangay

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# replace this to remote db in production
sqlite_filename = "database.db"
sqlite_url = f"sqlite:///{sqlite_filename}"

connect_args = {"check_same_thread": False}
db_engine = create_engine(sqlite_url, connect_args=connect_args)

def get_session():
    with Session(db_engine) as session:
        yield session

SessionDependency = Annotated[Session, Depends(get_session)]

def init_db_and_tables():
    logger.info("Creating database tables...")
    SQLModel.metadata.create_all(db_engine)

    logger.info("Initializing barangay table...")
    with Session(db_engine) as session:
        folder = Path("app/data/barangays")
        for file in folder.iterdir():
            if not file.is_file():
                logger.info(f"{file.name} is not a file, skipping...")
                continue

            barangay_json = None
            try:
                with open(file, "r") as file_read:
                    barangay_json = json.loads(file_read.read())
                logger.info(f"Successfully read JSON from {file.name}")
            except Exception as error:
                logger.warning(f"Could not read JSON from file {file.name} with error: {error}")
                continue

            if not barangay_json:
                logger.warning(f"No JSON read from {file.name}, skipping...")
                continue

            barangay_id = int(barangay_json["properties"]["barangay_id"])
            barangay_name = barangay_json["properties"]["barangay_name"]
            barangay_bounds = [(lat, long) for long, lat in barangay_json["geometry"]["coordinates"][0][0][1:]]
            barangay = session.exec(select(Barangay).where(Barangay.name == barangay_name)).first()
            if not barangay:
                barangay = Barangay(
                    barangay_id=barangay_id,
                    name=barangay_name,
                    bounds_coords=barangay_bounds
                )
                session.add(barangay)
                session.commit()
                logging.info(f"Barangay {barangay_name} instantiated in database")
            else:
                logging.info(f"Barangay {barangay_name} already exists in database")