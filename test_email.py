import os
import smtplib
from email.message import EmailMessage


EMAIL_ADDRESS = os.environ.get(
    "MANAS_EMAIL_ADDRESS"
)

EMAIL_APP_PASSWORD = os.environ.get(
    "MANAS_EMAIL_APP_PASSWORD"
)


msg = EmailMessage()

msg["Subject"] = "Manas Link Hub - SMTP Test"

msg["From"] = EMAIL_ADDRESS

msg["To"] = EMAIL_ADDRESS

msg.set_content(
    "Gmail SMTP is working correctly for Manas Link Hub."
)


with smtplib.SMTP(
    "smtp.gmail.com",
    587
) as smtp:

    smtp.starttls()

    smtp.login(
        EMAIL_ADDRESS,
        EMAIL_APP_PASSWORD
    )

    smtp.send_message(msg)


print(
    "SUCCESS: Test email sent."
)