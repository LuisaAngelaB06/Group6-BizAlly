import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        # Pulls the single URI we put in your .env
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except Exception as e:
        print(f"❌ Supabase Connection Failed: {e}")
        return None