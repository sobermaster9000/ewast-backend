from fastapi import APIRouter

router = APIRouter()

@router.get("/test", tags=["admin"])
async def test():
    return {"message": "Replace me"}