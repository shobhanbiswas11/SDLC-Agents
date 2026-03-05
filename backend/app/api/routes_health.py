from fastapi import APIRouter

from app.agents._llm import get_provider_info

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "llm": get_provider_info(),
    }
