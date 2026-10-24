"""Cookie-only authentication endpoints; tokens never appear in response JSON."""

import asyncio
import time

from fastapi import APIRouter, HTTPException, Request, Response

from backend.application.authentication.errors import (
    AuthenticationRequired,
    AuthenticationUnavailable,
    LoginLimited,
)

from .authentication_models import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    LoginInput,
    LoginResponse,
    PrincipalResponse,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def service(request: Request):
    value = getattr(request.app.state, "authentication", None)
    if value is None:
        raise HTTPException(503, detail={"code": "authentication_unavailable"})
    return value


def clear_cookies(response: Response, secure: bool) -> None:
    for name, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, "/api/auth")):
        response.delete_cookie(
            name, path=path, secure=secure, httponly=True, samesite="lax"
        )


def login_response(request: Request, result, response: Response) -> dict:
    now = int(time.time())
    secure = request.app.state.auth_secure_cookies
    for name, value, expiry, path in (
        (ACCESS_COOKIE, result.access_token, result.expires_at, "/"),
        (REFRESH_COOKIE, result.refresh_token, result.refresh_expires_at, "/api/auth"),
    ):
        response.set_cookie(
            name,
            value,
            max_age=max(0, expiry - now),
            path=path,
            secure=secure,
            httponly=True,
            samesite="lax",
        )
    return {
        "user_id": result.user_id,
        "expires_at": result.expires_at,
        "refresh_expires_at": result.refresh_expires_at,
    }


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginInput, response: Response):
    result = await asyncio.to_thread(
        service(request).login.execute,
        payload.login_id,
        payload.password,
        request.client.host if request.client else "unknown",
        int(time.time()),
    )
    return login_response(request, result, response)


@router.post("/refresh", response_model=LoginResponse)
async def refresh(request: Request, response: Response):
    result = await asyncio.to_thread(
        service(request).refresh.execute,
        request.cookies.get(REFRESH_COOKIE, ""),
        int(time.time()),
    )
    return login_response(request, result, response)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    await asyncio.to_thread(
        service(request).logout.execute, request.cookies.get(REFRESH_COOKIE, "")
    )
    clear_cookies(response, request.app.state.auth_secure_cookies)


@router.get("/me", response_model=PrincipalResponse)
async def me(request: Request):
    principal = request.scope["auth_principal"]
    return {"user_id": principal.user_id, "expires_at": principal.expires_at}


def register_authentication_errors(app) -> None:
    from fastapi.exception_handlers import request_validation_exception_handler
    from fastapi.exceptions import RequestValidationError
    from starlette.responses import JSONResponse

    @app.exception_handler(AuthenticationRequired)
    async def required(request, error):
        response = JSONResponse({"detail": {"code": error.code}}, status_code=401)
        if request.url.path.startswith("/api/auth/"):
            clear_cookies(
                response, getattr(request.app.state, "auth_secure_cookies", True)
            )
        return response

    @app.exception_handler(LoginLimited)
    async def limited(request, error):
        return JSONResponse(
            {"detail": {"code": "login_limited"}},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(AuthenticationUnavailable)
    async def unavailable(request, error):
        return JSONResponse(
            {"detail": {"code": "authentication_unavailable"}}, status_code=503
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        if request.url.path.startswith("/api/auth/"):
            return JSONResponse(
                {"detail": {"code": "invalid_authentication_input"}}, status_code=422
            )
        return await request_validation_exception_handler(request, error)
