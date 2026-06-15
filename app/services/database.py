from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

# replace this to remote db in production
sqlite_filename = "database.db"
sqlite_url = f"sqlite:///{sqlite_filename}"

connect_args = {"check_same_thread": False}
db_engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(db_engine)

def get_session():
    with Session(db_engine) as session:
        yield session

SessionDependency = Annotated[Session, Depends(get_session)]