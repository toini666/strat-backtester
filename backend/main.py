import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
except ModuleNotFoundError:  # pragma: no cover - optional in lightweight test envs
    Limiter = None
    RateLimitExceeded = None

    def get_remote_address(_: Request) -> str:
        return "local-test"

    def _rate_limit_exceeded_handler(*args, **kwargs):
        return None

load_dotenv()

from .api import router
from .market_data_routes import market_data_router

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address) if Limiter is not None else None

app = FastAPI(
    title="Nebular Apollo API",
    description="Backtesting Engine for Trading Strategies",
    version="1.0.0"
)

# Add rate limiter
app.state.limiter = limiter
if RateLimitExceeded is not None:
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

# In development, allow all origins if ALLOWED_ORIGINS is not set or contains "*"
if "*" in allowed_origins or os.getenv("ENV", "development") == "development":
    logger.warning("CORS is configured to allow all origins. This is not recommended for production.")
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(market_data_router)

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "online", "message": "Nebular Apollo Backtesting Engine Ready"}

@app.get("/health")
def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "cors_origins": allowed_origins if allowed_origins != ["*"] else "all"
    }
