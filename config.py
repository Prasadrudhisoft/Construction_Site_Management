from dbutils.pooled_db import PooledDB
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

############################### MYSQL CONFIGURATION ###############################
HOST = os.environ.get("DB_HOST")
DBNAME = os.environ.get("DB_NAME")
PASSWORD = os.environ.get("DB_PASSWORD")
USER = os.environ.get("DB_USER")

############################### CONNECTION POOL ###############################
pool = PooledDB(
    creator=pymysql,
    maxconnections=80,     # max total connections (important for 100 req/sec)
    mincached=2,           # initial idle connections
    maxcached=5,           # max idle connections
    blocking=True,          # wait if no connection available
    maxusage=1000,          # unlimited reuse
    setsession=[],          
    ping=1,                 # check connection health
    host=HOST,
    user=USER,
    password=PASSWORD,
    database=DBNAME,
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=5
)

############################### GET CONNECTION ###############################
def get_connection():
    conn = pool.connection()
    return conn