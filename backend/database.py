from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Read DATABASE_URL from .env
DATABASE_URL=os.getenv("DATABASE_URL")


# Create engine (actual connection to PostgreSQL)
engine= create_engine(
    DATABASE_URL,
    echo=True    # logs every SQL query in terminal - helpful during development
)

# Create SessionLocal
# Each request gets its own session, opens and closes cleanly
SessionLocal=sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create Base
# All your DB modeils will inherit from this
Base=declarative_base()

# Dependency - used in every route to get a DB session
def get_db():
    db=SessionLocal()
    try:
        yield db     # give the session to the route
    finally:
        db.close()   # always closes after request is done
