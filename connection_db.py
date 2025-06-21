import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Configuración de la base de datos
DB_CONFIG = {
   "host":  HOST,
    "database": DBNAME,
    "user": USER,
    "password": PASSWORD,
    "port":PORT
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

