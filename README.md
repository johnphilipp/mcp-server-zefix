# mcp-server-zefix

Look up any Swiss company directly from Claude.

[![PyPI](https://img.shields.io/pypi/v/mcp-server-zefix)](https://pypi.org/project/mcp-server-zefix/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/johnphilipp/mcp-server-zefix/actions/workflows/test.yml/badge.svg)](https://github.com/johnphilipp/mcp-server-zefix/actions/workflows/test.yml)

An [MCP](https://modelcontextprotocol.io/) server that connects Claude to [Zefix](https://www.zefix.ch/), Switzerland's official company register (Handelsregister). Zefix is operated by the Federal Office of Justice and provides authoritative data from all 26 cantonal commercial registers -- company details, legal forms, audit firms, corporate history, and official gazette publications.

## What you can ask

- "Search for Novartis on Zefix"
- "Find all foundations in Basel"
- "Who audits Novartis AG?"
- "What companies has Novartis taken over?"
- "Show me all branches of KIBAG Bauleistungen AG"
- "Get the corporate structure for CHE-467.005.033"
- "Show me the corporate history of Huber Baustoffe AG"
- "What capital changes has cohaga AG had recently?"
- "Find all GmbHs in Zurich"
- "List all Swiss legal forms in German"

## Quick Start

### Hosted (no installation)

Connect directly -- works in any MCP-compatible client.

**Claude Code:**

```bash
claude mcp add --transport http zefix https://mcp-server-zefix.contextfor.ai/mcp \
  --header "Authorization: Bearer <your-api-key>"
```

**Claude Desktop:**

Settings > Customize > Connectors > Add custom connector:
- URL: `https://mcp-server-zefix.contextfor.ai/mcp`

Request an API key at [zefix@contextfor.ai](mailto:zefix@contextfor.ai).

### Local (self-hosted)

```bash
claude mcp add zefix -- uvx mcp-server-zefix
```

Or add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "zefix": {
      "command": "uvx",
      "args": ["mcp-server-zefix"]
    }
  }
}
```

No API key or credentials needed for local usage.

## Tools

| Tool | Description |
|---|---|
| `search_companies` | Search by name (wildcards supported), filter by canton and legal form |
| `get_company_by_uid` | Full company profile: address, purpose, audit firm, takeover history, branch offices, previous names |
| `get_company_by_chid` | Same as above, using the CH-ID identifier |
| `get_company_structure` | Head office and all branch offices in a table with full addresses. Works from any branch UID. |
| `get_company_publications` | SHAB timeline: board changes, capital changes, mergers, address changes, and more |
| `list_legal_forms` | All Swiss legal forms (AG, GmbH, Stiftung, etc.) with IDs for filtering |

All tools accept a `language` parameter (de, fr, it, en). Output labels use official Zefix terminology in the selected language.

## What you get

A company lookup returns:

- **Identifiers** -- name, UID, CH-ID, status, legal form
- **Location** -- registered office, full address
- **Purpose** -- the company's stated business purpose
- **Audit firm** -- name and UID of the auditor
- **Corporate history** -- companies absorbed, acquisitions, previous names
- **Corporate structure** -- head office and all branch offices with addresses, displayed as a table
- **Branch offices** -- all registered branch locations
- **SHAB publications** -- timeline of legally significant events from the Swiss Official Gazette (board changes, capital changes, mergers, purpose changes)
- **Cantonal register link** -- direct link to the full excerpt with board members and signatories

## Configuration

Works with zero configuration using the public Zefix API. For the official authenticated API, set these environment variables:

| Variable | Default | Description |
|---|---|---|
| `ZEFIX_BASE_URL` | `https://www.zefix.ch/ZefixREST/api/v1` | API base URL |
| `ZEFIX_USERNAME` | _(none)_ | Username for ZefixPublicREST API |
| `ZEFIX_PASSWORD` | _(none)_ | Password for ZefixPublicREST API |

To use the official API, request credentials from `zefix@bj.admin.ch`, then:

```json
{
  "mcpServers": {
    "zefix": {
      "command": "uvx",
      "args": ["mcp-server-zefix"],
      "env": {
        "ZEFIX_BASE_URL": "https://www.zefix.admin.ch/ZefixPublicREST/api/v1",
        "ZEFIX_USERNAME": "your-username",
        "ZEFIX_PASSWORD": "your-password"
      }
    }
  }
}
```

## Development

```bash
git clone https://github.com/johnphilipp/mcp-server-zefix.git
cd mcp-server-zefix
uv sync --all-extras

uv run ruff check .           # lint
uv run pytest tests/ -v       # test (68 tests, all use fakes, no network)
npx @modelcontextprotocol/inspector uv --directory . run mcp-server-zefix  # interactive
```

## Architecture

Follows [Architecture Patterns with Python](https://www.cosmicpython.com/) (Percival & Gregory):

- **Domain models** (`models.py`) -- frozen dataclasses (`Company`, `LegalForm`, `ShabPublication`), domain exceptions, no infrastructure imports
- **Port + adapter** (`zefix_client.py`) -- `AbstractZefixClient` protocol; `HttpZefixClient` translates HTTP to domain objects and httpx exceptions to domain exceptions
- **Service layer** (`server.py`) -- `handle_*` functions accept the abstract client, never import httpx
- **Localization** (`i18n.py`) -- centralized label translations (de/fr/it/en) using official Zefix terminology
- **Fakes over mocks** -- tests use `FakeZefixClient`, a working in-memory implementation; test files never import httpx

## Self-hosting

The server supports remote deployment via Streamable HTTP transport. See `Dockerfile`, `docker-compose.prod.yml`, and `Caddyfile` for a Docker + Caddy setup with auto-HTTPS and API key authentication.

## License

MIT
