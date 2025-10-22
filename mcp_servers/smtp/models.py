from pydantic import BaseModel, Field

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
    to: list[str] = Field(..., description="Recipient email address.")
    subject: str = Field(..., description="Subject of the email.")
    body: str = Field(..., description="Body content of the email.")

# This file is no longer needed as the models have been moved to main.py
# It is kept for backward compatibility
