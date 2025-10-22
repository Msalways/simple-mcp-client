import asyncio
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
from typing import List, Dict, Any

from mcp.server import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("SMTP Server", instructions="""
This MCP server allows you to send emails using an SMTP server configuration.
              """)

config = {
    "host": os.getenv("SMTP_HOST"),
    "port": int(os.getenv("SMTP_PORT", 465)),
    "username": os.getenv("SMTP_USERNAME"),
    "password": os.getenv("SMTP_PASSWORD"),
}

@mcp.tool()
def send_email(to: List[str], subject: str, body: str) -> str:
    """
    Send an email using SMTP server configuration.

    Args:
        to: Recipient email addresses
        subject: Subject of the email
        body: Body content of the email
    """
    """ Send an email using the configured SMTP server."""
    try:
        print(config)
        msg = MIMEMultipart()
        msg["From"] = config["username"]
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        server = smtplib.SMTP_SSL(
            host=config["host"],
            port=config["port"],
            timeout=5
        )
        server.login(config["username"], config["password"])
        for recipient in to:
            server.sendmail(
                config["username"],
                recipient,
                msg.as_string()
            )
        time.sleep(2)
        return f"Email sent successfully"
    except Exception as e:
        return f"Error sending email: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")