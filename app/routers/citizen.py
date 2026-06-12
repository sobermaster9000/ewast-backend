from fastapi import APIRouter

router = APIRouter()

@router.get("/test", tags=["citizen"])
async def test():
    return {"message": "Replace me"}