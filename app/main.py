from fastapi import FastAPI

from app.database import Base, engine
from app.middleware.exception_handler import register_exception_handlers
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.routers import (
    auth_router, movie_router, theatre_router, show_router, booking_router, payment_router,
)

# Import all models so SQLAlchemy's metadata is aware of every table before create_all runs.
from app.models import user, movie, theatre, show, booking  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Movie Ticket Booking API",
    description=(
        "A production-style movie ticket booking backend with concurrency-safe "
        "seat reservation, JWT auth with refresh tokens, Redis caching, and a "
        "mock payment gateway."
    ),
    version="1.0.0",
)

# Order matters: logging wraps everything (outermost), rate limiting runs
# next, then the actual route handlers.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)

register_exception_handlers(app)

app.include_router(auth_router.router)
app.include_router(movie_router.router)
app.include_router(theatre_router.router)
app.include_router(show_router.router)
app.include_router(booking_router.router)
app.include_router(payment_router.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
