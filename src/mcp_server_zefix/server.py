"""MCP server for the Swiss Zefix company register."""

import logging

from mcp.server.fastmcp import FastMCP

from mcp_server_zefix.i18n import label, status_label
from mcp_server_zefix.models import (
    Company,
    CompanyRef,
    ZefixAPIError,
    ZefixConnectionError,
    ZefixError,
    ZefixTimeoutError,
    normalize_uid,
)
from mcp_server_zefix.zefix_client import AbstractZefixClient, HttpZefixClient

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "Zefix",
    instructions=(
        "Query the Swiss Zefix company register (Handelsregister). "
        "Search companies by name, look up by UID/CH-ID, and browse legal forms."
    ),
)

_client: AbstractZefixClient = HttpZefixClient()


def _format_company_summary(company: Company, language: str = "en") -> str:
    """Format a Company value object into a concise one-line Markdown summary."""
    parts = [f"**{company.name}**", f"{label('uid_label', language)}: {company.uid}"]
    if company.legal_form:
        parts.append(company.legal_form.name)
    location = company.legal_seat
    if company.canton:
        location += f" ({company.canton})"
    if location.strip():
        parts.append(location)
    if company.status:
        parts.append(f"[{status_label(company.status, language)}]")
    return " — ".join(parts)


def _format_company_detail(company: Company, language: str = "en") -> str:
    """Format a Company value object into detailed Markdown."""
    L = language  # noqa: N806
    status_display = status_label(company.status, L) if company.status else "N/A"
    lines = [
        f"# {company.name}",
        "",
        f"**{label('uid_label', L)}:** {company.uid}",
        f"**{label('chid_label', L)}:** {company.chid or 'N/A'}",
        f"**{label('status_label', L)}:** {status_display}",
        f"**{label('legal_form', L)}:** "
        f"{company.legal_form.name if company.legal_form else 'N/A'}",
        f"**{label('seat', L)}:** {company.legal_seat or 'N/A'}"
        + (f" ({company.canton})" if company.canton else ""),
    ]

    if company.address and company.address.format():
        lines.append(f"**{label('address', L)}:** {company.address.format()}")
    if company.purpose:
        lines.append(f"**{label('purpose', L)}:** {company.purpose}")
    if company.capital is not None:
        lines.append(
            f"**{label('capital', L)}:** "
            f"{company.capital_currency} {company.capital:,.0f}"
        )
    if company.shab_date:
        lines.append(f"**{label('shab_date', L)}:** {company.shab_date}")
    if company.delete_date:
        lines.append(f"**{label('delete_date', L)}:** {company.delete_date}")
    if company.cantonal_excerpt_url:
        lines.append(
            f"**{label('cantonal_excerpt', L)}:** {company.cantonal_excerpt_url}"
        )

    if company.audit_firms:
        firms = ", ".join(f"{f.name} ({f.uid})" for f in company.audit_firms)
        lines.append(f"**{label('audit_firms', L)}:** {firms}")

    if company.old_names:
        names = ", ".join(company.old_names)
        lines.append(f"**{label('old_names', L)}:** {names}")

    if company.taken_over:
        items = "\n".join(
            f"- {c.name} ({c.uid}), {c.legal_seat}" for c in company.taken_over
        )
        lines.append(f"**{label('has_taken_over', L)}:**\n{items}")

    if company.taken_over_by:
        items = ", ".join(f"{c.name} ({c.uid})" for c in company.taken_over_by)
        lines.append(f"**{label('taken_over_by', L)}:** {items}")

    if company.head_offices:
        items = ", ".join(
            f"{h.name} ({h.uid}), {h.legal_seat}" for h in company.head_offices
        )
        lines.append(f"**{label('head_offices_label', L)}:** {items}")

    if company.branch_offices:
        n = len(company.branch_offices)
        if n <= 10:
            items = "\n".join(
                f"- {b.name}, {b.legal_seat}" for b in company.branch_offices
            )
        else:
            items = "\n".join(
                f"- {b.name}, {b.legal_seat}"
                for b in company.branch_offices[:10]
            )
            items += f"\n- _... and {n - 10} more_"
        lines.append(
            f"**{label('branch_offices', L)} ({n}):**\n{items}"
        )

    return "\n\n".join(lines)


async def handle_search(
    client: AbstractZefixClient,
    name: str,
    canton: str = "",
    active_only: bool = True,
    language: str = "en",
    max_results: int = 20,
    offset: int = 0,
    legal_form_ids: list[int] | None = None,
) -> str:
    """Search for companies and return formatted Markdown results."""
    if (not name or name == "*") and not legal_form_ids:
        return (
            "Please provide a company name or a legal form filter. "
            "Use `*` with legal_form_ids to browse all companies of a type "
            "(e.g. legal_form_ids='7' for foundations)."
        )
    try:
        results = await client.search_companies(
            name,
            active_only=active_only,
            canton=canton,
            legal_form_ids=legal_form_ids,
            language=language,
            max_entries=max_results,
            offset=offset,
        )
    except ZefixConnectionError:
        return "Could not connect to the Zefix API."
    except ZefixTimeoutError:
        return "Request timed out."
    except ZefixAPIError as e:
        return f"Zefix API error (HTTP {e.status_code})."
    except ZefixError as e:
        logger.exception("Unexpected Zefix error during search")
        return f"An unexpected error occurred: {e}"

    if not results:
        return f"{label('no_companies_found', language)} '{name}'."

    lines = [f"Found {len(results)} {label('results_for', language)} **{name}**:\n"]
    for company in results:
        lines.append(f"- {_format_company_summary(company, language)}")

    if len(results) >= max_results:
        lines.append(
            f"\n_Showing first {max_results} results. "
            f"Use offset={offset + max_results} to see more._"
        )

    return "\n".join(lines)


async def handle_uid_lookup(
    client: AbstractZefixClient,
    uid: str,
    language: str = "en",
) -> str:
    """Look up a company by UID and return formatted details."""
    try:
        company = await client.get_company_by_uid(uid, language=language)
    except ZefixConnectionError:
        return "Could not connect to the Zefix API."
    except ZefixTimeoutError:
        return "Request timed out."
    except ZefixAPIError as e:
        return f"Zefix API error (HTTP {e.status_code})."
    except ZefixError as e:
        logger.exception("Unexpected Zefix error during UID lookup")
        return f"An unexpected error occurred: {e}"

    if company is None:
        normalized = normalize_uid(uid)
        return f"No company found with UID '{uid}' (searched as {normalized})."

    return _format_company_detail(company, language)


async def handle_chid_lookup(
    client: AbstractZefixClient,
    chid: str,
    language: str = "en",
) -> str:
    """Look up a company by CH-ID and return formatted details."""
    try:
        company = await client.get_company_by_chid(chid, language=language)
    except ZefixConnectionError:
        return "Could not connect to the Zefix API."
    except ZefixTimeoutError:
        return "Request timed out."
    except ZefixAPIError as e:
        return f"Zefix API error (HTTP {e.status_code})."
    except ZefixError as e:
        logger.exception("Unexpected Zefix error during CH-ID lookup")
        return f"An unexpected error occurred: {e}"

    if company is None:
        return f"No company found with CH-ID '{chid}'."

    return _format_company_detail(company, language)


async def handle_list_legal_forms(
    client: AbstractZefixClient,
    language: str = "en",
) -> str:
    """List all legal forms and return formatted Markdown."""
    try:
        forms = await client.list_legal_forms(language=language)
    except ZefixConnectionError:
        return "Could not connect to the Zefix API."
    except ZefixTimeoutError:
        return "Request timed out."
    except ZefixAPIError as e:
        return f"Zefix API error (HTTP {e.status_code})."
    except ZefixError as e:
        logger.exception("Unexpected Zefix error listing legal forms")
        return f"An unexpected error occurred: {e}"

    if not forms:
        return "No legal forms returned."

    lines = [f"# {label('legal_forms_title', language)}\n"]
    for form in sorted(forms, key=lambda f: f.id):
        lines.append(f"- **{form.name}** (ID: {form.id})")

    return "\n".join(lines)


async def handle_get_publications(
    client: AbstractZefixClient,
    uid: str,
    language: str = "en",
) -> str:
    """Get SHAB publications for a company and return formatted timeline."""
    try:
        publications = await client.get_company_publications(uid, language=language)
    except ZefixConnectionError:
        return "Could not connect to the Zefix API."
    except ZefixTimeoutError:
        return "Request timed out."
    except ZefixAPIError as e:
        return f"Zefix API error (HTTP {e.status_code})."
    except ZefixError as e:
        logger.exception("Unexpected Zefix error fetching publications")
        return f"An unexpected error occurred: {e}"

    if not publications:
        normalized = normalize_uid(uid)
        return f"No SHAB publications found for UID '{uid}' (searched as {normalized})."

    lines = [f"# {label('shab_publications', language)} ({len(publications)})\n"]
    for pub in publications:
        types_str = ", ".join(pub.mutation_types) if pub.mutation_types else "Update"
        lines.append(f"**{pub.date}** — {types_str}")
        if pub.message:
            lines.append(pub.message)
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def search_companies(
    name: str,
    canton: str = "",
    active_only: bool = True,
    language: str = "en",
    max_results: int = 20,
    offset: int = 0,
    legal_form_ids: str = "",
) -> str:
    """Search Swiss companies in the Zefix register by name.

    Use * as wildcard (e.g. "Novartis*" or "*pharma*"). Returns a list of
    matching companies with UID, legal form, and registered office.

    Args:
        name: Company name to search for. Supports * wildcard.
        canton: Two-letter canton code (e.g. ZH, BE, GE). Empty for all.
        active_only: If true, only return currently active companies.
        language: Response language (de, fr, it, en).
        max_results: Maximum number of results to return (1-100).
        offset: Pagination offset for retrieving additional results.
        legal_form_ids: Comma-separated legal form IDs (e.g. "3,4").
    """
    parsed_ids: list[int] | None = None
    if legal_form_ids:
        parsed_ids = [int(x.strip()) for x in legal_form_ids.split(",") if x.strip()]
    return await handle_search(
        _client,
        name,
        canton,
        active_only,
        language,
        max_results,
        offset,
        legal_form_ids=parsed_ids,
    )


@mcp.tool()
async def get_company_by_uid(uid: str, language: str = "en") -> str:
    """Get detailed information about a Swiss company by its UID number.

    The UID (Unternehmens-Identifikationsnummer) is the unique identifier
    for Swiss companies. Accepts various formats like CHE-123.456.789,
    CHE123456789, or just 123456789.

    Args:
        uid: Company UID in any format (e.g. CHE-123.456.789 or CHE123456789).
        language: Response language (de, fr, it, en).
    """
    return await handle_uid_lookup(_client, uid, language)


@mcp.tool()
async def get_company_by_chid(chid: str, language: str = "en") -> str:
    """Get detailed information about a Swiss company by its CH-ID.

    The CH-ID is an alternative identifier used in the Swiss commercial
    register system.

    Args:
        chid: The CH-ID identifier (e.g. CH27030000714).
        language: Response language (de, fr, it, en).
    """
    return await handle_chid_lookup(_client, chid, language)


@mcp.tool()
async def list_legal_forms(language: str = "en") -> str:
    """List all Swiss legal forms (Rechtsformen) recognized by Zefix.

    Useful for understanding legal form IDs returned in search results,
    or for filtering searches by legal form.

    Args:
        language: Language for legal form names (de, fr, it, en).
    """
    return await handle_list_legal_forms(_client, language)


@mcp.tool()
async def get_company_publications(uid: str, language: str = "en") -> str:
    """Get SHAB publications (Swiss Official Gazette) for a company.

    Returns a timeline of legally significant events: board changes,
    capital changes, mergers, address changes, purpose changes, etc.

    Args:
        uid: Company UID in any format (e.g. CHE-123.456.789 or CHE123456789).
        language: Response language (de, fr, it, en).
    """
    return await handle_get_publications(_client, uid, language)


_MAX_BRANCH_DETAIL_FETCHES = 50


def _format_address(company: Company) -> str:
    """Return formatted address, falling back to legal_seat."""
    if company.address and company.address.format():
        return company.address.format()
    return company.legal_seat


def _format_structure_table(
    head: Company,
    branches: list[Company | CompanyRef],
    *,
    capped: bool = False,
    language: str = "en",
    queried_uid: str = "",
) -> str:
    """Format a company structure as a Markdown table."""
    L = language  # noqa: N806
    queried_norm = normalize_uid(queried_uid) if queried_uid else ""
    uid_h = label("uid_label", L)
    lines = [
        f"# {label('company_structure', L)}: {head.name}\n",
        f"| # | {label('role', L)} | {label('name', L)} "
        f"| {uid_h} | {label('address_seat', L)} "
        f"| {label('status_label', L)} |",
        "|---|------|------|-----|----------------|--------|",
    ]

    def _row(
        num: str, role: str, name: str, uid: str, addr: str, st: str
    ) -> str:
        highlight = queried_norm and normalize_uid(uid) == queried_norm
        if highlight:
            return (
                f"| **{num}** | **{role}** | **{name}** "
                f"| **{uid}** | **{addr}** | **{st}** |"
            )
        return f"| {num} | {role} | {name} | {uid} | {addr} | {st} |"

    head_status = status_label(head.status, L)
    lines.append(
        _row(
            "1", label("head_office", L), head.name,
            head.uid, _format_address(head), head_status,
        )
    )

    branch_role = label("branch", L)
    for i, branch in enumerate(branches, start=2):
        if isinstance(branch, Company):
            address = _format_address(branch)
        else:
            address = branch.legal_seat
        st = status_label(branch.status, L)
        lines.append(
            _row(str(i), branch_role, branch.name, branch.uid, address, st)
        )

    if capped:
        notice = label("cap_notice", L).format(n=_MAX_BRANCH_DETAIL_FETCHES)
        lines.append(f"\n_{notice}_")

    return "\n".join(lines)


async def _fetch_branch_details(
    client: AbstractZefixClient,
    branch_refs: tuple[CompanyRef, ...],
    language: str,
) -> tuple[list[Company | CompanyRef], bool]:
    """Fetch full detail for branches (up to cap), fall back to ref.

    Returns (branches, capped) where capped is True when the cap was hit.
    """
    results: list[Company | CompanyRef] = []
    fetched = 0
    capped = False
    for ref in branch_refs:
        if fetched >= _MAX_BRANCH_DETAIL_FETCHES:
            capped = True
            results.append(ref)
            continue
        if not ref.ehraid:
            results.append(ref)
            continue
        try:
            company = await client.get_company_by_ehraid(
                ref.ehraid, language=language
            )
        except ZefixError as e:
            logger.debug("Failed to fetch detail for branch %s: %s", ref.uid, e)
            company = None
        results.append(company if company is not None else ref)
        fetched += 1
    return results, capped


async def handle_company_structure(
    client: AbstractZefixClient,
    uid: str,
    language: str = "en",
) -> str:
    """Look up a company's corporate structure (head office + branches)."""
    try:
        company = await client.get_company_by_uid(uid, language=language)
    except ZefixConnectionError:
        return "Could not connect to the Zefix API."
    except ZefixTimeoutError:
        return "Request timed out."
    except ZefixAPIError as e:
        return f"Zefix API error (HTTP {e.status_code})."
    except ZefixError as e:
        logger.exception("Unexpected Zefix error during structure lookup")
        return f"An unexpected error occurred: {e}"

    if company is None:
        normalized = normalize_uid(uid)
        return f"No company found with UID '{uid}' (searched as {normalized})."

    head: Company = company
    branch_refs: tuple[CompanyRef, ...] = ()

    # If this is a branch, navigate to its head office
    if company.head_offices:
        parent_uid = company.head_offices[0].uid
        try:
            parent = await client.get_company_by_uid(
                parent_uid, language=language
            )
        except (ZefixConnectionError, ZefixTimeoutError, ZefixAPIError, ZefixError):
            parent = None
        if parent is not None:
            head = parent
            branch_refs = parent.branch_offices
    elif company.branch_offices:
        branch_refs = company.branch_offices

    if not branch_refs:
        return label("no_structure", language)

    branches, capped = await _fetch_branch_details(
        client, branch_refs, language
    )
    return _format_structure_table(
        head, branches, capped=capped, language=language, queried_uid=uid
    )


@mcp.tool()
async def get_company_structure(uid: str, language: str = "en") -> str:
    """Get the corporate structure (head office and branches) of a Swiss company.

    Shows the parent company (Hauptniederlassung) and all its branch offices
    (Zweigniederlassungen) in a table with full addresses. Works whether you
    pass the UID of the head office or any branch — the full structure is
    returned either way.

    Fetches detail for up to 50 branches. May take a while for large
    structures since each branch requires a separate API call.

    Args:
        uid: Company UID in any format (e.g. CHE-105.807.648 or CHE123456789).
        language: Response language (de, fr, it, en).
    """
    return await handle_company_structure(_client, uid, language)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()
