"""Test fixtures and FakeZefixClient."""

from mcp_server_zefix.models import (
    Address,
    Company,
    LegalForm,
    ZefixError,
    normalize_uid,
)


def make_company(
    name: str = "Example AG",
    uid: str = "CHE-123.456.789",
    chid: str = "CH12345678901",
    status: str = "ACTIVE",
    legal_seat: str = "Zurich",
    canton: str = "ZH",
    legal_form: LegalForm | None = None,
    address: Address | None = None,
    purpose: str = "Development and sale of software.",
    capital: float | None = 100_000,
    capital_currency: str = "CHF",
    shab_date: str = "2024-06-15",
    cantonal_excerpt_url: str = "https://zh.chregister.ch/cr-portal/auszug/12345",
) -> Company:
    """Create a Company with sensible defaults. Override any field as needed."""
    if legal_form is None:
        legal_form = LegalForm(id=3, name="Corporation")
    if address is None:
        address = Address(street="Bahnhofstrasse 1", zip_code="8001", city="Zurich")
    return Company(
        name=name,
        uid=uid,
        chid=chid,
        status=status,
        legal_seat=legal_seat,
        canton=canton,
        legal_form=legal_form,
        address=address,
        purpose=purpose,
        capital=capital,
        capital_currency=capital_currency,
        shab_date=shab_date,
        cantonal_excerpt_url=cantonal_excerpt_url,
    )


def make_legal_form(
    id: int = 3,
    name: str = "Corporation",
) -> LegalForm:
    """Create a LegalForm with sensible defaults."""
    return LegalForm(id=id, name=name)


class FakeZefixClient:
    """In-memory fake of AbstractZefixClient for testing.

    Pass a domain exception to `error` to test error paths.
    """

    def __init__(
        self,
        companies: list[Company] | None = None,
        legal_forms: list[LegalForm] | None = None,
        error: ZefixError | None = None,
    ) -> None:
        self.companies: list[Company] = list(companies or [])
        self.legal_forms: list[LegalForm] = list(legal_forms or [])
        self.error = error

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
        if self.error:
            raise self.error

        query = name.replace("*", "").lower()
        results = [c for c in self.companies if query in c.name.lower()]

        if active_only:
            results = [c for c in results if c.status == "ACTIVE"]
        if canton:
            results = [c for c in results if c.canton.upper() == canton.upper()]

        return results[offset : offset + max_entries]

    async def get_company_by_uid(
        self, uid: str, *, language: str = "en"
    ) -> Company | None:
        if self.error:
            raise self.error

        normalized = normalize_uid(uid)
        for company in self.companies:
            if normalize_uid(company.uid) == normalized:
                return company
        return None

    async def get_company_by_chid(
        self, chid: str, *, language: str = "en"
    ) -> Company | None:
        if self.error:
            raise self.error

        for company in self.companies:
            if company.chid == chid:
                return company
        return None

    async def list_legal_forms(
        self, *, language: str = "de"
    ) -> list[LegalForm]:
        if self.error:
            raise self.error
        return list(self.legal_forms)
