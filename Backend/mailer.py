import json
import os
import shutil
import smtplib
import subprocess
from pathlib import Path
from email.message import EmailMessage

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
CONTACT_MAILER_SCRIPT = BASE_DIR / "Backend" / "mailers" / "contact_mailer.js"
NODEMAILER_MODULE = BASE_DIR / "node_modules" / "nodemailer"

load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "Backend" / ".env")


def send_contact_notification(payload):
    required_env = ("MAIL_USER", "MAIL_PASS", "CONTACT_RECEIVER")
    missing = [key for key in required_env if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing mail environment variables: {', '.join(missing)}")

    node_cmd = shutil.which("node") or shutil.which("node.exe")
    if not node_cmd or not NODEMAILER_MODULE.exists():
        return _send_contact_notification_smtp(payload)

    result = subprocess.run(
        [node_cmd, str(CONTACT_MAILER_SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(BASE_DIR),
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "Nodemailer failed"
        if "Cannot find module 'nodemailer'" in error:
            return _send_contact_notification_smtp(payload)
        raise RuntimeError(error)


def _send_contact_notification_smtp(payload):
    name = payload["name"]
    email = payload["email"]
    subject = payload["subject"]
    message = payload["message"]
    mail_user = os.getenv("MAIL_USER")
    mail_pass = (os.getenv("MAIL_PASS") or "").replace(" ", "")
    receiver = os.getenv("CONTACT_RECEIVER")

    email_message = EmailMessage()
    email_message["From"] = f"AlliTrack Contact Form <{mail_user}>"
    email_message["To"] = receiver
    email_message["Reply-To"] = email
    email_message["Subject"] = f"[AlliTrack Contact] {subject}"
    email_message.set_content(
        "\n".join([
            "New AlliTrack contact form message",
            "",
            f"Name: {name}",
            f"Email: {email}",
            f"Subject: {subject}",
            "",
            "Message:",
            message,
        ])
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(mail_user, mail_pass)
        smtp.send_message(email_message)
