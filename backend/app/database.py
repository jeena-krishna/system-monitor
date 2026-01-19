"""
database.py - Database Configuration

This file sets up the connection to SQLite and provides
the tools other files need to interact with the database.

Think of this as the "plumbing" - it connects your app
to the database so data can flow in and out.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL - tells SQLAlchemy where the database file lives
# "sqlite:///" means use SQLite, and "system_monitor.db" is the filename
# This file will be created automatically in your backend folder
DATABASE_URL = "sqlite:///system_monitor.db"

# The "engine" is the connection to the database
# It handles all the low-level communication
# check_same_thread=False is needed for SQLite to work with FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal is a factory that creates database sessions
# A "session" is like a conversation with the database -
# you open it, do your reads/writes, then close it
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class for all our database models
# Every table we create will inherit from this
Base = declarative_base()


def get_db():
    """
    Dependency function that provides a database session.
    
    FastAPI will call this automatically when an endpoint
    needs database access. It:
    1. Opens a session
    2. Gives it to the endpoint
    3. Closes it when done (even if there's an error)
    
    The "yield" keyword makes this a generator - it pauses
    after yielding the session and resumes to close it later.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()