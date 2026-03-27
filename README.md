# mcp-server-zefix

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for querying the Swiss [Zefix](https://www.zefix.ch/) company register (Zentraler Firmenindex / Handelsregister).

Search Swiss companies by name, look up detailed company information by UID or CH-ID, and browse legal forms -- all accessible as MCP tools from Claude Desktop, Claude Code, or any MCP-compatible client.

## Features

- **Search companies** by name with wildcard support, canton filter, and pagination
- **Look up companies** by UID (Unternehmens-Identifikationsnummer) or CH-ID
- **Browse legal forms** (Rechtsformen) recognized by the Swiss commercial register
- **Dual API support**: works out of the box with the public Zefix API (no credentials needed), with optional support for the official ZefixPublicREST API
- **Rate limiting** built in to respect Zefix API usage guidelines
- Accepts UID in any format (CHE-123.456.789, CHE123456789, 123456789)

## Available Tools

| Tool | Description |
|---|---|
| `search_companies` | Search companies by name with optional canton, status, and language filters |
| `get_company_by_uid` | Get full company details by UID number |
| `get_company_by_chid` | Get full company details by CH-ID |
| `list_legal_forms` | List all Swiss legal forms with their IDs |

## Installation

### Claude Desktop

Add to your `claude_desktop_config.json`:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

### Claude Code

```bash
claude mcp add zefix -- uvx mcp-server-zefix
```

### From source (development)

```bash
git clone https://github.com/johnphilipp/mcp-server-zefix.git
cd mcp-server-zefix
uv sync --all-extras
```

Then configure Claude Desktop to run from source:

```json
{
  "mcpServers": {
    "zefix": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/mcp-server-zefix", "run", "mcp-server-zefix"]
    }
  }
}
```

## Configuration

The server works out of the box with no configuration, using the public Zefix API.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ZEFIX_BASE_URL` | `https://www.zefix.ch/ZefixREST/api/v1` | API base URL |
| `ZEFIX_USERNAME` | _(none)_ | Username for ZefixPublicREST API |
| `ZEFIX_PASSWORD` | _(none)_ | Password for ZefixPublicREST API |

### Using the official ZefixPublicREST API

To use the officially documented API (recommended for production), request credentials by emailing `zefix@bj.admin.ch` with your name, organization, and intended use. Then configure:

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

## Architecture

This project follows principles from [Architecture Patterns with Python](https://www.cosmicpython.com/) (Percival & Gregory):

- **Domain models** (`models.py`): Immutable value objects (`Company`, `LegalForm`, `Address`) and domain exceptions (`ZefixConnectionError`, `ZefixTimeoutError`, etc.) -- the shared language of the Swiss commercial register, free of infrastructure dependencies
- **Abstract client protocol** (`zefix_client.py`): `AbstractZefixClient` is the port; `HttpZefixClient` is the adapter that translates HTTP responses to domain objects and httpx exceptions to domain exceptions
- **Service layer** (`server.py`): `handle_*` functions contain orchestration logic, depend on the abstract client, and catch only domain exceptions -- they never import httpx
- **Fakes over mocks**: Tests use `FakeZefixClient`, a working in-memory implementation -- no HTTP mocking libraries needed, test files never import httpx

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run linter
uv run ruff check .

# Run tests
uv run pytest tests/ -v

# Launch MCP Inspector for interactive testing
npx @modelcontextprotocol/inspector uv --directory . run mcp-server-zefix
```

## About Zefix

[Zefix](https://www.zefix.ch/) (Zentraler Firmenindex) is the central business name index of Switzerland, operated by the Federal Office of Justice. It provides access to company data from all cantonal commercial registers.

**Note:** Board members, signatories, and detailed corporate governance information are not available through Zefix. For this data, follow the cantonal register excerpt link (`cantonalExcerptWeb`) returned in company details.

## License

MIT
