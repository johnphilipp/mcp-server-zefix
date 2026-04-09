"""Domain models and exceptions for the Swiss Zefix company register."""

from dataclasses import dataclass


class ZefixError(Exception):
    """Base exception for all Zefix operations."""


class ZefixConnectionError(ZefixError):
    """Cannot reach the Zefix API."""


class ZefixTimeoutError(ZefixError):
    """Request to the Zefix API timed out."""


class ZefixAPIError(ZefixError):
    """The Zefix API returned an error response.

    Attributes:
        status_code: The HTTP status code (e.g. 500, 403).
    """

    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


class ZefixNotFoundError(ZefixError):
    """No entity found for the given identifier."""


@dataclass(frozen=True)
class Address:
    """A Swiss postal address."""

    street: str = ""
    zip_code: str = ""
    city: str = ""

    def format(self) -> str:
        """Format as a single-line address string."""
        parts = [self.street, " ".join(filter(None, [self.zip_code, self.city]))]
        return ", ".join(p for p in parts if p.strip())


@dataclass(frozen=True)
class LegalForm:
    """A Swiss legal form (Rechtsform).

    Examples: AG (Aktiengesellschaft), GmbH, Einzelunternehmen.
    The name is pre-resolved to the requested language.
    """

    id: int
    name: str


@dataclass(frozen=True)
class CompanyRef:
    """A lightweight reference to another company.

    Used for audit firms, takeover history, and branch offices.
    """

    name: str
    uid: str
    legal_seat: str = ""
    status: str = ""
    ehraid: int = 0


@dataclass(frozen=True)
class Company:
    """A company entry in the Swiss Zefix register.

    Immutable value object. Companies are read-only snapshots
    from the register.
    """

    name: str
    uid: str
    chid: str = ""
    status: str = ""
    legal_seat: str = ""
    canton: str = ""
    legal_form: LegalForm | None = None
    address: Address | None = None
    purpose: str = ""
    capital: float | None = None
    capital_currency: str = "CHF"
    shab_date: str = ""
    delete_date: str | None = None
    cantonal_excerpt_url: str = ""
    audit_firms: tuple[CompanyRef, ...] = ()
    taken_over: tuple[CompanyRef, ...] = ()
    taken_over_by: tuple[CompanyRef, ...] = ()
    branch_offices: tuple[CompanyRef, ...] = ()
    head_offices: tuple[CompanyRef, ...] = ()
    old_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ShabPublication:
    """A SHAB (Swiss Official Gazette of Commerce) publication entry."""

    date: str
    message: str
    mutation_types: tuple[str, ...] = ()


def normalize_uid(uid: str) -> str:
    """Normalize a UID to the format expected by the Zefix API.

    Accepts: CHE-123.456.789, CHE123456789, CHE 123 456 789, 123456789.
    Returns: CHE123456789
    """
    cleaned = uid.replace("-", "").replace(".", "").replace(" ", "").strip()
    if cleaned.isdigit():
        cleaned = f"CHE{cleaned}"
    return cleaned.upper()
