import pytest
from backend.presentation.chat_routes import ChatRequest
from backend.presentation.chat_websocket_routes import WebSocketChatRequest
from pydantic import ValidationError


@pytest.mark.parametrize("count", [1, 9, 50])
@pytest.mark.parametrize("request_type", [ChatRequest, WebSocketChatRequest])
def test_chat_accepts_up_to_fifty_distinct_products(count, request_type):
    codes = [f"{i:012}" for i in range(count)]
    request = request_type.model_validate(
        {
            "product_yj_codes": codes,
            "message": "テスト質問",
            "messages": [{"role": "user", "content": "テスト質問"}],
        }
    )
    assert request.product_yj_codes == codes


@pytest.mark.parametrize("count", [0, 51])
@pytest.mark.parametrize("request_type", [ChatRequest, WebSocketChatRequest])
def test_chat_rejects_out_of_range_product_counts(count, request_type):
    with pytest.raises(ValidationError):
        request_type.model_validate(
            {
                "product_yj_codes": [f"{i:012}" for i in range(count)],
                "message": "テスト質問",
                "messages": [{"role": "user", "content": "テスト質問"}],
            }
        )
