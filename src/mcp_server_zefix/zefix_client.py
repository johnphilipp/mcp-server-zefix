"""Zefix API client: abstract protocol (port) and HTTP implementation (adapter)."""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import httpx

from mcp_server_zefix.models import (
    Address,
    Company,
    CompanyRef,
    LegalForm,
    ShabPublication,
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
        legal_form_ids: list[int] | None = None,
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

    async def list_legal_forms(self, *, language: str = "de") -> list[LegalForm]: ...

    async def get_company_publications(
        self, uid: str, *, language: str = "en"
    ) -> list[ShabPublication]: ...


_DEFAULT_BASE_URL = "https://www.zefix.ch/ZefixREST/api/v1"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
_REQUEST_TIMEOUT = 30.0
_MIN_REQUEST_INTERVAL = 1.0  # seconds

# The unauthenticated API uses German status values
_STATUS_MAP = {
    "EXISTIEREND": "ACTIVE",
    "GELOESCHT": "DELETED",
}


_MUTATION_TYPE_LABELS = {
    "kapitalaenderung": "Capital change",
    "kapitalaenderung.libriert": "Capital paid in",
    "kapitalaenderung.nominell": "Nominal capital change",
    "kapitalaenderung.stueckelung": "Share denomination change",
    "aenderungorgane": "Board/management change",
    "adressaenderung": "Address change",
    "zweckaenderung": "Purpose change",
    "neueintr": "New registration",
    "mutation": "Mutation",
    "loeschung": "Deletion",
    "konkurs": "Bankruptcy",
    "fusion": "Merger",
    "umwandlung": "Conversion",
    "spaltung": "Demerger",
    "revisionsstelle": "Audit firm change",
}

_XML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_xml_tags(text: str) -> str:
    """Remove XML/HTML tags from SHAB message text."""
    return _XML_TAG_RE.sub("", text).replace("&apos;", "'").replace("&amp;", "&")


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


def _parse_company_refs(items: Any) -> tuple[CompanyRef, ...]:
    """Parse a list of company references from the API response."""
    if not items:
        return ()
    refs = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        uid = raw.get("uidFormatted") or raw.get("uid", "")
        status = _STATUS_MAP.get(raw.get("status", ""), raw.get("status", ""))
        refs.append(
            CompanyRef(
                name=raw.get("name", ""),
                uid=uid,
                legal_seat=raw.get("legalSeat", ""),
                status=status,
            )
        )
    return tuple(refs)


def _parse_old_names(items: Any) -> tuple[str, ...]:
    """Parse old company names from the API response."""
    if not items:
        return ()
    return tuple(
        item["name"] for item in items if isinstance(item, dict) and "name" in item
    )


def _parse_company(
    raw: dict[str, Any],
    language: str,
    legal_forms_map: dict[int, LegalForm] | None = None,
) -> Company:
    """Map a raw API response dict to a Company domain object.

    Handles both the /firm/ endpoint shape (unauthenticated) and
    the /company/ endpoint shape (authenticated).
    """
    # Address: present in /company/ and /firm/{ehraid} detail responses
    addr_raw = raw.get("address") or {}
    if addr_raw:
        street = addr_raw.get("street", "")
        house_number = addr_raw.get("houseNumber", "")
        if house_number:
            street = f"{street} {house_number}".strip()
        address = Address(
            street=street,
            zip_code=addr_raw.get("swissZipCode", ""),
            city=addr_raw.get("city", "") or addr_raw.get("town", ""),
        )
    else:
        address = None

    # Legal form: nested object in /company/, integer ID in /firm/
    legal_form = _parse_legal_form(raw.get("legalForm"), language)
    if legal_form is None and legal_forms_map is not None:
        lf_id = raw.get("legalFormId")
        if lf_id is not None:
            legal_form = legal_forms_map.get(int(lf_id))

    # UID: use formatted version if available, fall back to raw
    uid = raw.get("uidFormatted") or raw.get("uid", "")

    # Status: map German values to English
    raw_status = raw.get("status", "")
    status = _STATUS_MAP.get(raw_status, raw_status)

    return Company(
        name=raw.get("name", "Unknown"),
        uid=uid,
        chid=raw.get("chidFormatted") or raw.get("chid", ""),
        status=status,
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
        audit_firms=_parse_company_refs(raw.get("auditFirms")),
        taken_over=_parse_company_refs(raw.get("hasTakenOver")),
        taken_over_by=_parse_company_refs(raw.get("wasTakenOverBy")),
        branch_offices=_parse_company_refs(raw.get("branchOffices")),
        old_names=_parse_old_names(raw.get("oldNames")),
    )


@dataclass
class HttpZefixClient:
    """Real Zefix API client over HTTP.

    Uses the unauthenticated /firm/ endpoints by default (same as the
    zefix.ch frontend). Supports the official ZefixPublicREST /company/
    endpoints when credentials are provided via ZEFIX_USERNAME / ZEFIX_PASSWORD.

    All httpx exceptions are translated to domain exceptions in _request.
    """

    base_url: str = field(
        default_factory=lambda: os.getenv("ZEFIX_BASE_URL", _DEFAULT_BASE_URL)
    )
    username: str | None = field(default_factory=lambda: os.getenv("ZEFIX_USERNAME"))
    password: str | None = field(default_factory=lambda: os.getenv("ZEFIX_PASSWORD"))
    _last_request_time: float = field(default=0.0, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _legal_forms_cache: dict[str, dict[int, LegalForm]] = field(
        default_factory=dict, init=False, repr=False
    )

    @property
    def _is_authenticated(self) -> bool:
        return bool(self.username and self.password)

    @property
    def _auth(self) -> httpx.BasicAuth | None:
        if self._is_authenticated:
            return httpx.BasicAuth(self.username, self.password)  # type: ignore[arg-type]
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
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "application/json, text/plain, */*",
                },
            ) as client:
                logger.debug("Zefix API %s %s", method, path)
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 404:
                raise ZefixNotFoundError(f"Not found: {method} {path}") from e
            raise ZefixAPIError(
                f"HTTP {status} from Zefix API: {method} {path}",
                status_code=status,
            ) from e
        except httpx.TimeoutException as e:
            raise ZefixTimeoutError(f"Request timed out: {method} {path}") from e
        except httpx.ConnectError as e:
            raise ZefixConnectionError(
                f"Cannot connect to Zefix API at {self.base_url}: {e}"
            ) from e
        except httpx.HTTPError as e:
            raise ZefixError(f"Unexpected Zefix API error: {method} {path}: {e}") from e

    async def _get_company_detail(self, ehraid: int, language: str) -> Company:
        """Fetch full company detail via /firm/{ehraid}/withoutShabPub.json."""
        data = await self._request("GET", f"/firm/{ehraid}/withoutShabPub.json")
        lf_map = await self._get_legal_forms_map(language)
        return _parse_company(data, language, lf_map)

    async def _get_legal_forms_map(self, language: str) -> dict[int, LegalForm]:
        """Get a cached mapping of legal form ID -> LegalForm."""
        if language not in self._legal_forms_cache:
            forms = await self.list_legal_forms(language=language)
            self._legal_forms_cache[language] = {f.id: f for f in forms}
        return self._legal_forms_cache[language]

    async def search_companies(
        self,
        name: str,
        *,
        active_only: bool = True,
        canton: str = "",
        legal_form_ids: list[int] | None = None,
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
        if legal_form_ids:
            body["legalForms"] = legal_form_ids

        if self._is_authenticated:
            data = await self._request("POST", "/company/search", json=body)
            if not data:
                return []
            items = data if isinstance(data, list) else [data]
            return [_parse_company(item, language) for item in items]

        # Unauthenticated: use /firm/search.json
        data = await self._request("POST", "/firm/search.json", json=body)
        if not data:
            return []
        items = data.get("list", []) if isinstance(data, dict) else data
        if not items:
            return []
        lf_map = await self._get_legal_forms_map(language)
        return [_parse_company(item, language, lf_map) for item in items]

    async def get_company_by_uid(
        self, uid: str, *, language: str = "en"
    ) -> Company | None:
        uid_clean = normalize_uid(uid)

        if self._is_authenticated:
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

        # Unauthenticated: search to find ehraid, then fetch full detail
        uid_formatted = (
            f"{uid_clean[:3]}-{uid_clean[3:6]}.{uid_clean[6:9]}.{uid_clean[9:]}"
        )
        data = await self._request(
            "POST",
            "/firm/search.json",
            json={
                "name": uid_formatted,
                "activeOnly": False,
                "languageKey": language,
                "maxEntries": 1,
            },
        )
        if not data:
            return None
        items = data.get("list", []) if isinstance(data, dict) else data
        if not items:
            return None
        # Verify exact UID match and fetch detail
        for item in items:
            item_uid = item.get("uidFormatted") or item.get("uid", "")
            if normalize_uid(item_uid) == uid_clean:
                ehraid = item.get("ehraid")
                if ehraid is not None:
                    return await self._get_company_detail(ehraid, language)
                lf_map = await self._get_legal_forms_map(language)
                return _parse_company(item, language, lf_map)
        return None

    async def get_company_by_chid(
        self, chid: str, *, language: str = "en"
    ) -> Company | None:
        if self._is_authenticated:
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

        # Unauthenticated: search to find ehraid, then fetch full detail
        data = await self._request(
            "POST",
            "/firm/search.json",
            json={
                "name": chid,
                "activeOnly": False,
                "languageKey": language,
                "maxEntries": 1,
            },
        )
        if not data:
            return None
        items = data.get("list", []) if isinstance(data, dict) else data
        if not items:
            return None
        for item in items:
            item_chid = (item.get("chidFormatted") or item.get("chid", "")).replace(
                "-", ""
            )
            if item_chid == chid.replace("-", ""):
                ehraid = item.get("ehraid")
                if ehraid is not None:
                    return await self._get_company_detail(ehraid, language)
                lf_map = await self._get_legal_forms_map(language)
                return _parse_company(item, language, lf_map)
        return None

    async def list_legal_forms(self, *, language: str = "de") -> list[LegalForm]:
        if self._is_authenticated:
            data = await self._request(
                "GET", "/legalForm", params={"languageKey": language}
            )
        else:
            data = await self._request("GET", "/legalForm.json")
        if not data:
            return []
        items = data if isinstance(data, list) else [data]
        result = []
        for item in items:
            lf = _parse_legal_form(item, language)
            if lf is not None:
                result.append(lf)
        return result

    async def _find_ehraid(self, uid: str, language: str) -> int | None:
        """Search by UID and return the ehraid if found."""
        uid_clean = normalize_uid(uid)
        uid_formatted = (
            f"{uid_clean[:3]}-{uid_clean[3:6]}.{uid_clean[6:9]}.{uid_clean[9:]}"
        )
        data = await self._request(
            "POST",
            "/firm/search.json",
            json={
                "name": uid_formatted,
                "activeOnly": False,
                "languageKey": language,
                "maxEntries": 1,
            },
        )
        if not data:
            return None
        items = data.get("list", []) if isinstance(data, dict) else data
        for item in items:
            item_uid = item.get("uidFormatted") or item.get("uid", "")
            if normalize_uid(item_uid) == uid_clean:
                return item.get("ehraid")
        return None

    async def get_company_publications(
        self, uid: str, *, language: str = "en"
    ) -> list[ShabPublication]:
        ehraid = await self._find_ehraid(uid, language)
        if ehraid is None:
            return []
        data = await self._request("GET", f"/firm/{ehraid}/shabPub.json")
        if not data:
            return []
        items = data if isinstance(data, list) else [data]
        publications = []
        for item in items:
            mutation_keys = [m.get("key", "") for m in item.get("mutationTypes", [])]
            labels = tuple(_MUTATION_TYPE_LABELS.get(k, k) for k in mutation_keys)
            publications.append(
                ShabPublication(
                    date=item.get("shabDate", ""),
                    message=_strip_xml_tags(item.get("message", "")),
                    mutation_types=labels,
                )
            )
        return publications
