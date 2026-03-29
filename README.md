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
- "Show me the corporate history of Huber Baustoffe AG"
- "What capital changes has cohaga AG had recently?"
- "Find all GmbHs in Zurich"
- "List all Swiss legal forms in English"

## Quick Start

### Claude Code

```bash
claude mcp add zefix -- uvx mcp-server-zefix
```

### Claude Desktop

Add to your `claude_desktop_config.json` (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

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

No API key or credentials needed. Works out of the box.

## Tools

| Tool | Description |
|---|---|
| `search_companies` | Search by name (wildcards supported), filter by canton and legal form |
| `get_company_by_uid` | Full company profile: address, purpose, audit firm, takeover history, branch offices, previous names |
| `get_company_by_chid` | Same as above, using the CH-ID identifier |
| `get_company_publications` | SHAB timeline: board changes, capital changes, mergers, address changes, and more |
| `list_legal_forms` | All Swiss legal forms (AG, GmbH, Stiftung, etc.) with IDs for filtering |

## What you get

A company lookup returns:

- **Identifiers** -- name, UID, CH-ID, status, legal form
- **Location** -- registered office, full address
- **Purpose** -- the company's stated business purpose
- **Audit firm** -- name and UID of the auditor
- **Corporate history** -- companies absorbed, acquisitions, previous names
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
uv run pytest tests/ -v       # test (50 tests, all use fakes, no network)
npx @modelcontextprotocol/inspector uv --directory . run mcp-server-zefix  # interactive
```

## Architecture

Follows [Architecture Patterns with Python](https://www.cosmicpython.com/) (Percival & Gregory):

- **Domain models** (`models.py`) -- frozen dataclasses (`Company`, `LegalForm`, `ShabPublication`), domain exceptions, no infrastructure imports
- **Port + adapter** (`zefix_client.py`) -- `AbstractZefixClient` protocol; `HttpZefixClient` translates HTTP to domain objects and httpx exceptions to domain exceptions
- **Service layer** (`server.py`) -- `handle_*` functions accept the abstract client, never import httpx
- **Fakes over mocks** -- tests use `FakeZefixClient`, a working in-memory implementation; test files never import httpx

## License

MIT
