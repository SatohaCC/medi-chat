"""システム診断、医薬品カタログ、チャット、WebSocketストリーミング用APIルーター"""

from __future__ import annotations

from .chat_routes import router as chat_router
from .chat_websocket_routes import router as chat_websocket_router
from .health_routes import router as health_router
from .medicine_routes import router as medicine_router
from .search_routes import router as search_router

__all__ = [
    "health_router",
    "medicine_router",
    "search_router",
    "chat_router",
    "chat_websocket_router",
]
