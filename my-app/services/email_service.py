import os
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv


load_dotenv()


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_REMETENTE = os.getenv("SMTP_EMAIL")
PASSWORD_EMAIL = os.getenv("SMTP_PASSWORD")


def enviar_codigo_recuperacao(email, codigo):

    if not EMAIL_REMETENTE:
        raise ValueError(
            "SMTP_EMAIL não está definido no ficheiro .env"
        )

    if not PASSWORD_EMAIL:
        raise ValueError(
            "SMTP_PASSWORD não está definido no ficheiro .env"
        )


    mensagem = EmailMessage()

    mensagem["Subject"] = "Recuperação da password"
    mensagem["From"] = EMAIL_REMETENTE
    mensagem["To"] = email

    mensagem.set_content(
        f"""
Olá,

Foi solicitado um código para redefinir a password
da sua conta.

O seu código de recuperação é:

{codigo}

Este código é válido durante 5 minutos.

Se não solicitou a recuperação da password,
ignore este email.

Cumprimentos,
Dataeme
"""
    )


    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT
    ) as smtp:

        smtp.ehlo()

        smtp.starttls()

        smtp.ehlo()

        smtp.login(
            EMAIL_REMETENTE,
            PASSWORD_EMAIL
        )

        smtp.send_message(mensagem)