from app.models.schemas import ChatResponse


def test_chat_response_model_imports():
    assert ChatResponse is not None
