"""
Compare SQLite and Supabase data to verify migration
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import CodeReview

def compare_databases(sqlite_url, postgres_url):
    """Compare record counts and sample data"""
    print("Comparing databases...")
    
    # SQLite
    sqlite_engine = create_engine(sqlite_url)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_db = SqliteSession()
    
    # Supabase
    postgres_engine = create_engine(postgres_url)
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_db = PostgresSession()
    
    # Compare counts
    sqlite_count = sqlite_db.query(CodeReview).count()
    postgres_count = postgres_db.query(CodeReview).count()
    
    print(f"\nRecord counts:")
    print(f"  SQLite:   {sqlite_count}")
    print(f"  Supabase: {postgres_count}")
    
    if sqlite_count == postgres_count:
        print("✓ Counts match!")
    else:
        print("⚠ Counts don't match")
    
    # Compare sample data
    if sqlite_count > 0 and postgres_count > 0:
        sqlite_latest = sqlite_db.query(CodeReview).order_by(CodeReview.id.desc()).first()
        postgres_latest = postgres_db.query(CodeReview).order_by(CodeReview.id.desc()).first()
        
        print(f"\nLatest records:")
        print(f"  SQLite:   {sqlite_latest.repository} - {sqlite_latest.language}")
        print(f"  Supabase: {postgres_latest.repository} - {postgres_latest.language}")
    
    sqlite_db.close()
    postgres_db.close()

if __name__ == "__main__":
    import sys
    import os
    
    sqlite_url = "sqlite:///./patent_review.db"
    
    # Get Supabase URL from .env.supabase
    if os.path.exists(".env.supabase"):
        with open(".env.supabase") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    postgres_url = line.split("=", 1)[1].strip()
                    break
        
        compare_databases(sqlite_url, postgres_url)
    else:
        print("Error: .env.supabase not found")
        sys.exit(1)