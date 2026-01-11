import psycopg
from psycopg import sql
from dotenv import load_dotenv
import os, json, time
from psycopg import OperationalError
from queue import Queue
from threading import Thread

load_dotenv()

dbq = Queue(maxsize=1000)

def connect_db():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_DB"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )
    conn.autocommit = True

    return conn

def insert_row(conn, param: dict):
    if len(param["fields"]) != len(param["values"]):
        raise ValueError("Length of fields and values are not equal.")

    query = sql.SQL("""
        INSERT INTO {table} ({fields})
        VALUES ({placeholders})
    """).format(
        table=sql.Identifier(param["table"]),
        fields=sql.SQL(', ').join(map(sql.Identifier, param["fields"])),
        placeholders=sql.SQL(', ').join(sql.Placeholder() for _ in param["values"])
    )

    with conn.cursor() as cur:
        cur.execute(query, param["values"])

def db_worker():
    conn = None

    while True:
        param = dbq.get()

        while True:
            try:
                if conn is None or conn.closed:
                    conn = connect_db()

                insert_row(conn, param)
                dbq.task_done()
                break

            except OperationalError as e:
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass
                conn = None
                time.sleep(1)

            except Exception as e:
                print("DB insert failed (non-connection error):", repr(e))
                dbq.task_done()
                break

def queue_db_write(param: dict):
    dbq.put(param)

