from fastapi import APIRouter

router = APIRouter()


@router.post("/turn")
async def chat_turn(message: dict):
    # Placeholder — integrate LangChain later
    return {"reply": "Chat processing not implemented yet."}