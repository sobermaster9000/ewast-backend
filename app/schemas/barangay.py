from pydantic import BaseModel

class Barangay(BaseModel):
    barangay_id: int
    name: str
    bounds_coords: list[tuple[float, float]]