import asyncio
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
from typing import List

from pydantic import BaseModel, Field
from mcp.server import FastMCP
from dotenv import load_dotenv

# Define models directly in this file to avoid import issues
class SMTPServerConfig(BaseModel):
    """
    Model for SMTP server configuration.
    """
    host: str = Field(..., description="The hostname or IP address of the SMTP server.")
    port: int = Field(..., description="The port number of the SMTP server.")
    username: str = Field(..., description="The username for authenticating with the SMTP server.")
    password: str = Field(..., description="The password for authenticating with the SMTP server.")

class SMTPMessageInput(BaseModel):
    """
    Model for input data to send via SMTP.
    """
    to: List[str] = Field(..., description="Recipient email address.")
    subject: str = Field(..., description="Subject of the email.")
    body: str = Field(..., description="Body content of the email.")

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
def send_email(input_data: SMTPMessageInput) -> str:
    """
    Send an email using SMTP server configuration.

    Args:
        input_data: The email details to send
    """
    """ Send an email using the configured SMTP server."""
    try:
        print(config)
        msg = MIMEMultipart()
        msg["From"] = config["username"]
        msg["Subject"] = input_data.subject
        msg.attach(MIMEText(input_data.body, "plain"))
        
        server = smtplib.SMTP_SSL(
            host=config["host"],
            port=config["port"],
            timeout=5
        )
        server.login(config["username"], config["password"])
        for recipient in input_data.to:
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