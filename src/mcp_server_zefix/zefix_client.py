"""Zefix API client: abstract protocol (port) and HTTP implementation (adapter)."""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import httpx

from mcp_server_zefix.models import (
    Address,
    Company,
    LegalForm,
    ZefixAPIError,
    ZefixConnectionError,
    ZefixError,
    ZefixNotFoundError,
    ZefixTimeoutError,
    normalize_uid,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class AbstractZefixClient(Protocol):
    """Abstract interface for querying the Swiss Zefix register.

    All methods raise only domain exceptions (ZefixError subclasses).
    """

    async def search_companies(
        self,
        name: str,
        *,
        active_only: bool = True,
        canton: str = "",
        language: str = "en",
        max_entries: int = 20,
        offset: int = 0,
    ) -> list[Company]: ...

    async def get_company_by_uid(
        self, uid: str, *, language: str = "en"
    ) -> Company | None: ...

    async def get_company_by_chid(
        self, chid: str, *, language: str = "en"
    ) -> Company | None: ...

    async def list_legal_forms(
        self, *, language: str = "de"
    ) -> list[LegalForm]: ...


_DEFAULT_BASE_URL = "https://www.zefix.ch/ZefixREST/api/v1"
_USER_AGENT = "mcp-server-zefix/0.1.0"
_REQUEST_TIMEOUT = 30.0
_MIN_REQUEST_INTERVAL = 1.0  # seconds


def _parse_legal_form(raw: Any, language: str) -> LegalForm | None:
    """Parse a legal form from the API's varying response shapes."""
    if not isinstance(raw, dict):
        return None
    fid = raw.get("id")
    if fid is None:
        return None
    name_field = raw.get("name", {})
    if isinstance(name_field, dict):
        name = name_field.get(language) or name_field.get("de", "")
    elif isinstance(name_field, str):
        name = name_field
    else:
        name = ""
    return LegalForm(id=int(fid), name=name)


def _parse_company(raw: dict[str, Any], language: str) -> Company:
    """Map a raw API response dict to a Company domain object."""
    addr_raw = raw.get("address") or {}
    address = (
        Address(
            street=addr_raw.get("street", ""),
            zip_code=addr_raw.get("swissZipCode", ""),
            city=addr_raw.get("city", ""),
        )
        if addr_raw
        else None
    )

    legal_form = _parse_legal_form(raw.get("legalForm"), language)

    return Company(
        name=raw.get("name", "Unknown"),
        uid=raw.get("uid", ""),
        chid=raw.get("chid", ""),
        status=raw.get("status", ""),
        legal_seat=raw.get("legalSeat", ""),
        canton=raw.get("canton", ""),
        legal_form=legal_form,
        address=address,
        purpose=raw.get("purpose", ""),
        capital=raw.get("capital"),
        capital_currency=raw.get("capitalCurrency", "CHF"),
        shab_date=raw.get("shabDate", ""),
        delete_date=raw.get("deleteDate"),
        cantonal_excerpt_url=raw.get("cantonalExcerptWeb", ""),
    )


@dataclass
class HttpZefixClient:
    """Real Zefix API client over HTTP.

    Supports the unauthenticated ZefixREST API (default) and the official
    ZefixPublicREST API (via env vars ZEFIX_USERNAME / ZEFIX_PASSWORD).
    All httpx exceptions are translated to domain exceptions in _request.
    """

    base_url: str = field(
        default_factory=lambda: os.getenv("ZEFIX_BASE_URL", _DEFAULT_BASE_URL)
    )
    username: str | None = field(
        default_factory=lambda: os.getenv("ZEFIX_USERNAME")
    )
    password: str | None = field(
        default_factory=lambda: os.getenv("ZEFIX_PASSWORD")
    )
    _last_request_time: float = field(default=0.0, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    @property
    def _auth(self) -> httpx.BasicAuth | None:
        if self.username and self.password:
            return httpx.BasicAuth(self.username, self.password)
        return None

    async def _throttle(self) -> None:
        """Enforce minimum interval between requests."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < _MIN_REQUEST_INTERVAL:
                await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make a throttled request.

        Translates all httpx exceptions to domain exceptions.
        """
        await self._throttle()
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=_REQUEST_TIMEOUT,
                auth=self._auth,
                headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
            ) as client:
                logger.debug("Zefix API %s %s", method, path)
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 404:
                raise ZefixNotFoundError(
                    f"Not found: {method} {path}"
                ) from e
            raise ZefixAPIError(
                f"HTTP {status} from Zefix API: {method} {path}",
                status_code=status,
            ) from e
        except httpx.TimeoutException as e:
            raise ZefixTimeoutError(
                f"Request timed out: {method} {path}"
            ) from e
        except httpx.ConnectError as e:
            raise ZefixConnectionError(
                f"Cannot connect to Zefix API at {self.base_url}: {e}"
            ) from e
        except httpx.HTTPError as e:
            raise ZefixError(
                f"Unexpected Zefix API error: {method} {path}: {e}"
            ) from e

    async def search_companies(
        self,
        name: str,
        *,
        active_only: bool = True,
        canton: str = "",
        language: str = "en",
        max_entries: int = 20,
        offset: int = 0,
    ) -> list[Company]:
        max_entries = max(1, min(max_entries, 100))
        body: dict[str, Any] = {
            "name": name,
            "activeOnly": active_only,
            "languageKey": language,
            "maxEntries": max_entries,
            "offset": offset,
        }
        if canton:
            body["canton"] = canton.upper()

        data = await self._request("POST", "/company/search", json=body)
        if not data:
            return []
        items = data if isinstance(data, list) else [data]
        return [_parse_company(item, language) for item in items]

    async def get_company_by_uid(
        self, uid: str, *, language: str = "en"
    ) -> Company | None:
        uid_clean = normalize_uid(uid)
        try:
            data = await self._request(
                "GET",
                f"/company/uid/{uid_clean}",
                params={"languageKey": language},
            )
        except ZefixNotFoundError:
            return None
        if not data:
            return None
        items = data if isinstance(data, list) else [data]
        return _parse_company(items[0], language) if items else None

    async def get_company_by_chid(
        self, chid: str, *, language: str = "en"
    ) -> Company | None:
        try:
            data = await self._request(
                "GET",
                f"/company/chid/{chid}",
                params={"languageKey": language},
            )
        except ZefixNotFoundError:
            return None
        if not data:
            return None
        items = data if isinstance(data, list) else [data]
        return _parse_company(items[0], language) if items else None

    async def list_legal_forms(
        self, *, language: str = "de"
    ) -> list[LegalForm]:
        data = await self._request(
            "GET", "/legalForm", params={"languageKey": language}
        )
        if not data:
            return []
        items = data if isinstance(data, list) else [data]
        result = []
        for item in items:
            lf = _parse_legal_form(item, language)
            if lf is not None:
                result.append(lf)
        return result
