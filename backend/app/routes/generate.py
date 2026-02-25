from fastapi import APIRouter
from app.agent.graph import run_generation
from app.schemas.request.generate_request import GenerateRequest
from app.schemas.response.generate_response import GenerateResponse

router = APIRouter()


@router.post("/", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    result = run_generation(text=req.text, spec=req.spec)
    return result