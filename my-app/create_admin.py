import re
from config import supabase, ph



def create_admin(username, password):
    password_hash = ph.hash(password)

    utilizador = {
        "username": username,
        "password": password_hash,
        "is_admin": True
    }

    response = (
        supabase
        .table("utilizador")
        .insert(utilizador)
        .execute()
    )

create_admin("Dataeme", "Dataeme123")