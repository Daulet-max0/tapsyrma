"""
Email хабарлама (SMTP) — конфиг орнатылса ғана жіберіледі.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def is_enabled() -> bool:
    return bool(config.MAIL_ENABLED and config.SMTP_HOST and config.SMTP_FROM)


def send_email(to: str, subject: str, body: str) -> bool:
    if not to or not is_enabled():
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.SMTP_FROM
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
            if config.SMTP_USE_TLS:
                server.starttls()
            if config.SMTP_USER and config.SMTP_PASSWORD:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_FROM, [to], msg.as_string())
        return True
    except Exception:
        return False


def notify_achievement_approved(teacher_email: str, title: str) -> bool:
    subject = "Ustaz Rating — жетістігіңіз расталды ✅"
    body = (
        "Сәлеметсіз бе!\n\n"
        f"Сіздің «{title}» жетістігіңіз админ тарапынан расталды.\n"
        "Профильде жаңа ұпайыңызды көре аласыз.\n\n"
        "— Ustaz Rating, Түркістан колледжі"
    )
    return send_email(teacher_email, subject, body)
