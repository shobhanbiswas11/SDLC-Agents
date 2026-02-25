from fastapi import FastAPI
from app.routes import chat, generate

app = FastAPI(title="Code Generator Agent")

app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(generate.router, prefix="/generate", tags=["Generate"])


@app.get("/")
async def health():
    return {"status": "ok"}