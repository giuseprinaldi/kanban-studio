import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure data directory exists
DB_DIR = "/app/data"
if not os.path.exists(DB_DIR):
    try:
        os.makedirs(DB_DIR)
    except Exception:
        # Fallback to local directory if running outside Docker/without permissions
        DB_DIR = "."

DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'pm.db')}"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
