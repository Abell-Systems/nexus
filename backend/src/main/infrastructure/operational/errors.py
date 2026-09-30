from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from application.matching.find_assets import UnknownDemandError
from infrastructure.operational.router import MVP_PATHS

_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


def _is_mvp(request: Request) -> bool:
    return request.url.path in MVP_PATHS


def install_error_contract(app: FastAPI) -> None:
    """Stable {code, message} errors for the MVP routes only; every other route keeps its own error shape."""

    @app.exception_handler(UnknownDemandError)
    async def unknown_demand(request: Request, exc: UnknownDemandError) -> JSONResponse:
        return _error(404, "DEMAND_NOT_FOUND", f"La demanda '{exc.args[0]}' no existe.")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        if not _is_mvp(request):
            return await request_validation_exception_handler(request, exc)
        field = exc.errors()[0]["loc"][-1]
        return _error(422, "INVALID_REQUEST", f"Valor no válido para el parámetro '{field}'.")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        if not _is_mvp(request):
            return await http_exception_handler(request, exc)
        return _error(exc.status_code, _HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}"), "Solicitud no válida.")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        if not _is_mvp(request):
            raise exc
        return _error(500, "INTERNAL_ERROR", "Error interno.")
