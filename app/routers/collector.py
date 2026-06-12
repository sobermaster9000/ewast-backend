from fastapi import APIRouter

router = APIRouter()

@router.get("/test", tags=["collector"])
async def test():
    return {"message": "Replace me"}