from email.message import EmailMessage
from email.policy import default


def export_as_eml(
    subject: str,
    body: str,
    to_email: str | None = None,
    from_email: str | None = None,
) -> bytes:
    """
    Exports the generated email draft as a standard .eml file.
    """
    msg = EmailMessage(policy=default)
    msg["Subject"] = subject
    if from_email:
        msg["From"] = from_email
    if to_email:
        msg["To"] = to_email
    msg.set_content(body)
    return msg.as_bytes()
