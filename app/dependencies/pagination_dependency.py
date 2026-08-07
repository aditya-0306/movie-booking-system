from fastapi import Query

from app.schemas.common_schema import PaginationParams


def pagination_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)
