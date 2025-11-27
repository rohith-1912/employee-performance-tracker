from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# SQLite database URL (the file will be created in the backend folder)
SQLALCHEMY_DATABASE_URL = "sqlite:///./employee_performance.db"

# Create the SQLAlchemy engine (responsible for the connection to the database)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed only for SQLite
)

# SessionLocal is a class we will use to create database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our ORM models (tables will inherit from this)
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session.
    It opens a session at the start of a request and closes it when done.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
