import mysql.connector
import os
from dotenv import load_dotenv

# Load the environment variables from your .env file
load_dotenv()

def get_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT")),
            # This line uses the ca.pem file you just downloaded
            ssl_ca=os.getenv("DB_SSL_CA")
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        return None