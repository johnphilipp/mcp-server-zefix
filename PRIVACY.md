# Privacy Policy

**mcp-server-zefix** is an open-source MCP server that queries publicly available data from the Swiss Zefix company register (Handelsregister) and the Swiss Official Gazette of Commerce (SHAB/SOGC).

## Data we collect

**No personal data is collected.** This server has no authentication, no user accounts, and no tracking.

## Logging

Tool calls are logged for operational purposes (monitoring server health, diagnosing errors). Logs may include:

- Timestamps
- MCP session identifiers (opaque, not linked to individuals)
- Tool names and query parameters (e.g., company names searched)
- Response times and error codes

Logs are retained on the server for up to 30 days and are not shared with third parties.

## Third-party APIs

Your queries are passed to the following public Swiss government APIs:

- **Zefix API** ([zefix.ch](https://www.zefix.ch/)) — operated by the Swiss Federal Office of Justice
- **SHAB/SOGC API** — Swiss Official Gazette of Commerce

These services have their own privacy policies. We do not control how they process requests.

## Cookies and tracking

None. No cookies, no analytics, no fingerprinting.

## Contact

For questions about this privacy policy: [zefix@contextfor.ai](mailto:zefix@contextfor.ai)

## Changes

This policy may be updated. Changes are tracked in the [Git history](https://github.com/johnphilipp/mcp-server-zefix/commits/main/PRIVACY.md).
