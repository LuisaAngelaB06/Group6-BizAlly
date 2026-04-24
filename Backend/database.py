import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # your mysql password
        database="allitrack"  # USE YOUR CURRENT DB NAME
    )
    return conn