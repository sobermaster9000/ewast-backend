from sqlmodel import SQLModel, Field

class Summary(SQLModel, table=True):
    summary_id: int | None = Field(default=None, primary_key=True)
    general_summary: str | None = Field(default=None)