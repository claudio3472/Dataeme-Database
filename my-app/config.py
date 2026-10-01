import os

from dotenv import load_dotenv
from supabase import create_client, Client
from argon2 import PasswordHasher

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Define SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no ficheiro .env"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ph = PasswordHasher()