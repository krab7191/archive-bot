from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote
from os import environ
from sqlalchemy import URL
import psycopg2

database = environ.get("database")

password = environ.get("password")
host = environ.get("host")
user = environ.get("user")
port = environ.get("port")

url_object = URL.create(
    "postgresql+psycopg2",
    username=user,
    password=password,
    host=host,
    database=database,
)


engine = create_engine(
    url_object,
    pool_size=2,
    max_overflow=0,
    # echo=True,
    pool_pre_ping=True
)

session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
Base = declarative_base()
