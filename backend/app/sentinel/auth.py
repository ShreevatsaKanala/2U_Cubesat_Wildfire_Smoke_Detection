from __future__ import annotations

import asyncio
import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TOKEN_ENDPOINT = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)


class SentinelAuth:
    """OAuth2 client-credentials authenticator for Copernicus Data Space."""

    def __init__(self) -> None:
        self._token: str = ""
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()
        self._authenticated = False

    @property
    def authenticated(self) -> bool:
        return self._authenticated and self._token and time.time() < self._expires_at

    async def get_token(self) -> str:
        if self.authenticated:
            return self._token
        async with self._lock:
            if self.authenticated:
                return self._token
            await self._refresh_token()
            return self._token

    async def _refresh_token(self) -> None:
        client_id = settings.SH_CLIENT_ID
        client_secret = settings.SH_CLIENT_SECRET
        if not client_id or not client_secret:
            logger.warning("Sentinel Hub credentials not configured")
            self._authenticated = False
            return

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    TOKEN_ENDPOINT,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )
                resp.raise_for_status()
                body = resp.json()
                self._token = body["access_token"]
                expires_in = body.get("expires_in", 600)
                self._expires_at = time.time() + max(expires_in - 30, 30)
                self._authenticated = True
                logger.info("Sentinel Hub token refreshed successfully")
        except httpx.TimeoutException:
            logger.warning("Sentinel Hub token request timed out")
            self._authenticated = False
        except httpx.HTTPStatusError as exc:
            logger.warning("Sentinel Hub token error: HTTP %s", exc.response.status_code)
            self._authenticated = False
        except Exception as exc:
            logger.warning("Sentinel Hub token error: %s", exc)
            self._authenticated = False

    def is_authenticated(self) -> bool:
        return self.authenticated
