from fastapi import APIRouter
from .health import router as health_router
from .users import router as users_router
from .chat import router as chat_router
from .codeforces import router as codeforces_router
from .memory import router as memory_router
from .agents import router as agents_router
from .recommendations import router as recommendations_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(users_router)
api_router.include_router(chat_router)
api_router.include_router(codeforces_router)
api_router.include_router(memory_router)
api_router.include_router(agents_router)
api_router.include_router(recommendations_router)

__all__ = ["api_router"]
