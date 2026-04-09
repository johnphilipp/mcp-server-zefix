import argparse

from mcp_server_zefix.server import main

parser = argparse.ArgumentParser(
    description="MCP server for the Swiss Zefix company register"
)
parser.add_argument(
    "--transport",
    choices=["stdio", "streamable-http"],
    default="stdio",
    help="Transport protocol (default: stdio)",
)
args = parser.parse_args()
main(transport=args.transport)
