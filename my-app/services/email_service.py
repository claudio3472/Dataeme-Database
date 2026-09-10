import os
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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



def enviar_nota_encomenda(email, PDF):

    if not EMAIL_REMETENTE:
        raise ValueError(
            "SMTP_EMAIL não está definido no ficheiro .env"
        )

    if not PDF:
        raise ValueError(
            "PDF não existe"
        )

    mensagem = EmailMessage()

    mensagem["Subject"] = "Nota de encomenda"
    mensagem["From"] = EMAIL_REMETENTE
    mensagem["To"] = email

    mensagem.set_content("Nota de Encomenda em anexo.")

    with open(PDF, "rb") as f:
        dados_pdf = f.read()

    mensagem.add_attachment(
        dados_pdf,
        maintype="application",
        subtype="pdf",
        filename=os.path.basename(PDF)
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(EMAIL_REMETENTE, PASSWORD_EMAIL)
        smtp.send_message(mensagem)