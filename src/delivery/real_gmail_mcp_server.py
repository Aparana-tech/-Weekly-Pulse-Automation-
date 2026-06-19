import asyncio
import base64
import logging
import os
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("real_gmail_mcp_server")

# Load Google Credentials
creds = None
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose"
]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
if os.path.exists(TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
else:
    logger.error("token.json not found! Please run scripts/authenticate_google.py first.")

server = Server("gmail")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools for Gmail integration."""
    return [
        types.Tool(
            name="create_draft",
            description="Create an email draft in Gmail.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Comma separated list of email addresses"},
                    "subject": {"type": "string"},
                    "body": {"type": "string", "description": "HTML body of the email"}
                },
                "required": ["to", "subject", "body"],
            },
        ),
        types.Tool(
            name="send_email",
            description="Send an email directly via Gmail.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Comma separated list of email addresses"},
                    "subject": {"type": "string"},
                    "body": {"type": "string", "description": "HTML body of the email"}
                },
                "required": ["to", "subject", "body"],
            },
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool execution requests."""
    
    if not creds:
        return [types.TextContent(
            type="text",
            text="Error: Missing or invalid Google Credentials. Please run scripts/authenticate_google.py."
        )]
        
    try:
        service = build("gmail", "v1", credentials=creds)
        
        to = arguments["to"]
        subject = arguments["subject"]
        body = arguments["body"]
        
        message = MIMEText(body, "html")
        message["to"] = to
        message["subject"] = subject
        
        raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        if name == "create_draft":
            body_dict = {"message": {"raw": raw_msg}}
            draft = service.users().drafts().create(userId="me", body=body_dict).execute()
            
            return [types.TextContent(
                type="text",
                text=f"Draft created successfully. ID: {draft['id']}"
            )]
            
        elif name == "send_email":
            body_dict = {"raw": raw_msg}
            sent = service.users().messages().send(userId="me", body=body_dict).execute()
            
            return [types.TextContent(
                type="text",
                text=f"Email sent successfully. ID: {sent['id']}"
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
