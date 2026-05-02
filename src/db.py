import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="videodb",
        user="postgres",
        password="Shaheer2006",
        host="localhost",
        port="5432"
    )