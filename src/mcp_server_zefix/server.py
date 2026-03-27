"""MCP server for the Swiss Zefix company register."""

import logging

from mcp.server.fastmcp import FastMCP

from mcp_server_zefix.models import (
    Company,
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
    description=(
        "Query the Swiss Zefix company register (Handelsregister). "
        "Search companies by name, look up by UID/CH-ID, and browse legal forms."
    ),
)

_client: AbstractZefixClient = HttpZefixClient()


def _format_company_summary(company: Company) -> str:
    """Format a Company value object into a concise one-line Markdown summary."""
    parts = [f"**{company.name}**", f"UID: {company.uid}"]
    if company.legal_form:
        parts.append(company.legal_form.name)
    location = company.legal_seat
    if company.canton:
        location += f" ({company.canton})"
    if location.strip():
        parts.append(location)
    if company.status:
        parts.append(f"[{company.status}]")
    return " — ".join(parts)


def _format_company_detail(company: Company) -> str:
    """Format a Company value object into detailed Markdown."""
    lines = [
        f"# {company.name}",
        "",
        f"**UID:** {company.uid}",
        f"**CH-ID:** {company.chid or 'N/A'}",
        f"**Status:** {company.status or 'N/A'}",
        f"**Legal form:** {company.legal_form.name if company.legal_form else 'N/A'}",
        f"**Registered office:** {company.legal_seat or 'N/A'}"
        + (f" ({company.canton})" if company.canton else ""),
    ]

    if company.address and company.address.format():
        lines.append(f"**Address:** {company.address.format()}")
    if company.purpose:
        lines.append(f"**Purpose:** {company.purpose}")
    if company.capital is not None:
        lines.append(f"**Capital:** {company.capital_currency} {company.capital:,.0f}")
    if company.shab_date:
        lines.append(f"**Last SHAB publication:** {company.shab_date}")
    if company.delete_date:
        lines.append(f"**Deletion date:** {company.delete_date}")
    if company.cantonal_excerpt_url:
        lines.append(f"**Cantonal register excerpt:** {company.cantonal_excerpt_url}")

    return "\n\n".join(lines)


async def handle_search(
    client: AbstractZefixClient,
    name: str,
    canton: str = "",
    active_only: bool = True,
    language: str = "en",
    max_results: int = 20,
    offset: int = 0,
) -> str:
    """Search for companies and return formatted Markdown results."""
    try:
        results = await client.search_companies(
            name,
            active_only=active_only,
            canton=canton,
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
        return f"No companies found matching '{name}'."

    lines = [f"Found {len(results)} result(s) for **{name}**:\n"]
    for company in results:
        lines.append(f"- {_format_company_summary(company)}")

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

    return _format_company_detail(company)


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

    return _format_company_detail(company)


async def handle_list_legal_forms(
    client: AbstractZefixClient,
    language: str = "de",
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

    lines = ["# Swiss Legal Forms (Rechtsformen)\n"]
    for form in sorted(forms, key=lambda f: f.id):
        lines.append(f"- **{form.name}** (ID: {form.id})")

    return "\n".join(lines)


@mcp.tool()
async def search_companies(
    name: str,
    canton: str = "",
    active_only: bool = True,
    language: str = "en",
    max_results: int = 20,
    offset: int = 0,
) -> str:
    """Search Swiss companies in the Zefix register by name.

    Use * as wildcard (e.g. "Novartis*" or "*pharma*"). Returns a list of
    matching companies with UID, legal form, and registered office.

    Args:
        name: Company name to search for. Supports * wildcard.
        canton: Two-letter canton code to filter by (e.g. ZH, BE, GE). Empty for all cantons.
        active_only: If true, only return currently active companies.
        language: Response language (de, fr, it, en).
        max_results: Maximum number of results to return (1-100).
        offset: Pagination offset for retrieving additional results.
    """
    return await handle_search(
        _client, name, canton, active_only, language, max_results, offset
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
async def list_legal_forms(language: str = "de") -> str:
    """List all Swiss legal forms (Rechtsformen) recognized by Zefix.

    Useful for understanding legal form IDs returned in search results,
    or for filtering searches by legal form.

    Args:
        language: Language for legal form names (de, fr, it, en).
    """
    return await handle_list_legal_forms(_client, language)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()
