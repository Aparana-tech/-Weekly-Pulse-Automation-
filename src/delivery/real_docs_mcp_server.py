import asyncio
import json
import logging
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("real_docs_mcp_server")

# Load Google Credentials
creds = None
SCOPES = ["https://www.googleapis.com/auth/documents"]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
if os.path.exists(TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
else:
    logger.error("token.json not found! Please run scripts/authenticate_google.py first.")

server = Server("google-docs")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools for Google Docs integration."""
    return [
        types.Tool(
            name="get_document",
            description="Get the contents of a Google Document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "documentId": {"type": "string"},
                },
                "required": ["documentId"],
            },
        ),
        types.Tool(
            name="batch_update",
            description="Apply a batch of updates (text, formatting, tables) to a Google Document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "documentId": {"type": "string"},
                    "requests": {
                        "type": "array",
                        "items": {"type": "object"}
                    },
                },
                "required": ["documentId", "requests"],
            },
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool execution requests."""
    
    if not creds or not creds.valid:
        return [types.TextContent(
            type="text",
            text="Error: Missing or invalid Google Credentials. Please run scripts/authenticate_google.py."
        )]
        
    try:
        service = build("docs", "v1", credentials=creds)
        
        if name == "get_document":
            document_id = arguments["documentId"]
            doc = service.documents().get(documentId=document_id).execute()
            
            # Simple content extraction for checking existence
            content_blocks = []
            for element in doc.get("body", {}).get("content", []):
                if "paragraph" in element:
                    for p_element in element["paragraph"].get("elements", []):
                        if "textRun" in p_element:
                            content_blocks.append({"text": p_element["textRun"]["content"]})
                            
            # Return JSON string representing the simplified content array
            return [types.TextContent(
                type="text",
                text=json.dumps({"content": content_blocks})
            )]

        elif name == "batch_update":
            document_id = arguments["documentId"]
            requests = arguments["requests"]
            
            result = service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
            
            return [types.TextContent(
                type="text",
                text=f"Batch update completed successfully: {json.dumps(result)}"
            )]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
