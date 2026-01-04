"""
Migrate database schema to Supabase (Postgres) and optionally migrate data from local SQLite.

- Creates tables based on SQLAlchemy Base.metadata (PatentTranslation, TerminologyEntry)
- Optionally migrates existing data from a local SQLite DB into Supabase
"""

import os
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db_base import Base
from app.models import PatentTranslation, TerminologyEntry


def check_connection(engine) -> bool:
    """Test database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print("✓ Connected to database")
            print(f"  PostgreSQL version: {version[:60]}...")
            return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def create_tables(engine) -> bool:
    """Create all tables"""
    try:
        print("\nCreating tables...")
        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✓ Tables created/found: {tables}")

        # Print columns for key tables (if present)
        for tname in ["patent_translations", "terminology"]:
            if tname in tables:
                columns = [col["name"] for col in inspector.get_columns(tname)]
                print(f"✓ {tname} columns: {columns}")

        return True
    except Exception as e:
        print(f"✗ Table creation failed: {e}")
        return False


def _sqlite_path_from_url(sqlite_url: str) -> str:
    # sqlite:///./xxx.db -> ./xxx.db
    if sqlite_url.startswith("sqlite:///"):
        return sqlite_url.replace("sqlite:///", "", 1)
    if sqlite_url.startswith("sqlite://"):
        return sqlite_url.replace("sqlite://", "", 1)
    return sqlite_url


def migrate_data(source_url: str, target_engine) -> bool:
    """
    Migrate existing data from SQLite to Supabase.
    Migrates:
      - PatentTranslation
      - TerminologyEntry (with upsert-like behavior on japanese_term)
    """
    try:
        sqlite_path = _sqlite_path_from_url(source_url)

        if not os.path.exists(sqlite_path):
            print(f"ℹ No local database found to migrate from: {sqlite_path}")
            return True

        print(f"\nMigrating data from SQLite: {sqlite_path}")

        source_engine = create_engine(source_url)
        SourceSession = sessionmaker(bind=source_engine)
        TargetSession = sessionmaker(bind=target_engine)

        source_db = SourceSession()
        target_db = TargetSession()

        try:
            # -------------------------
            # 1) Patent translations
            # -------------------------
            translations = source_db.query(PatentTranslation).all()
            print(f"Found {len(translations)} translations to migrate")

            migrated_trans = 0
            for row in translations:
                # Create new object WITHOUT id
                new_row = PatentTranslation(
                    source_text=row.source_text,
                    source_language=row.source_language,
                    translation=row.translation,
                    target_language=row.target_language,
                    patent_id=row.patent_id,
                    section_type=row.section_type,
                    domain=row.domain,
                    confidence_score=row.confidence_score,
                    terminology_matches=row.terminology_matches or 0,
                    file_name=row.file_name,
                    created_at=row.created_at,  # ok if None; Postgres default will fill on insert if omitted
                    translated_by=row.translated_by,
                    retrieved_examples=row.retrieved_examples,
                )

                # If created_at is None, omit it to let server_default work (more consistent)
                if row.created_at is None:
                    new_row.created_at = None

                target_db.add(new_row)
                migrated_trans += 1

                # Commit in batches to avoid huge transactions
                if migrated_trans % 500 == 0:
                    target_db.commit()
                    print(f"  ... migrated {migrated_trans}/{len(translations)} translations")

            target_db.commit()
            print(f"✓ Migrated {migrated_trans} translations successfully")

            # -------------------------
            # 2) Terminology (upsert-like)
            # -------------------------
            terms = source_db.query(TerminologyEntry).all()
            print(f"Found {len(terms)} terminology entries to migrate")

            migrated_terms = 0
            updated_terms = 0

            for term in terms:
                jt = (term.japanese_term or "").strip()
                if not jt:
                    continue

                existing = (
                    target_db.query(TerminologyEntry)
                    .filter(TerminologyEntry.japanese_term == jt)
                    .one_or_none()
                )

                if existing is None:
                    new_term = TerminologyEntry(
                        japanese_term=jt,
                        chinese_term=term.chinese_term,
                        domain=term.domain,
                        usage_count=term.usage_count or 0,
                        last_used=term.last_used,
                        added_by=term.added_by,
                        verified=term.verified or 0,
                        notes=term.notes,
                    )
                    target_db.add(new_term)
                    migrated_terms += 1
                else:
                    # Update existing
                    existing.chinese_term = term.chinese_term
                    existing.domain = term.domain
                    existing.usage_count = term.usage_count or existing.usage_count or 0
                    existing.last_used = term.last_used or existing.last_used
                    existing.added_by = term.added_by or existing.added_by
                    existing.verified = term.verified if term.verified is not None else existing.verified
                    existing.notes = term.notes or existing.notes
                    updated_terms += 1

                if (migrated_terms + updated_terms) % 500 == 0:
                    target_db.commit()
                    print(
                        f"  ... processed {migrated_terms + updated_terms}/{len(terms)} terminology entries"
                    )

            target_db.commit()
            print(f"✓ Migrated {migrated_terms} new terminology entries")
            if updated_terms > 0:
                print(f"✓ Updated {updated_terms} existing terminology entries")

            return True

        finally:
            source_db.close()
            target_db.close()

    except Exception as e:
        print(f"✗ Data migration failed: {e}")
        return False


def main() -> None:
    print("=" * 60)
    print("Supabase Migration Tool")
    print("=" * 60)

    db_url = settings.DATABASE_URL
    print(f"\nTarget database: {db_url[:70]}...")

    if "sqlite" in db_url:
        print("\n⚠ Warning: DATABASE_URL is still pointing to SQLite")
        print("Please switch env to Supabase/Postgres first.")
        sys.exit(1)

    if "supabase" not in db_url and "postgres" not in db_url:
        print("\n⚠ Warning: DATABASE_URL doesn't look like Supabase/Postgres")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            sys.exit(1)

    engine = create_engine(db_url)

    print("\nStep 1: Testing connection...")
    if not check_connection(engine):
        sys.exit(1)

    print("\nStep 2: Creating schema...")
    if not create_tables(engine):
        sys.exit(1)

    print("\nStep 3: Data migration...")
    migrate = input("Migrate data from local SQLite? (yes/no): ").strip().lower()
    if migrate == "yes":
        # Prefer a likely local DB name; you can change this to your real one.
        candidates = [
            "sqlite:///./patent_translation.db",
            "sqlite:///./patent_ai.db",
            "sqlite:///./patent_review.db",
        ]

        chosen: Optional[str] = None
        for c in candidates:
            if os.path.exists(_sqlite_path_from_url(c)):
                chosen = c
                break

        if chosen is None:
            print("\nCouldn't find a local SQLite db among:")
            for c in candidates:
                print(f"  - {_sqlite_path_from_url(c)}")
            manual = input("\nEnter sqlite url (e.g. sqlite:///./xxx.db) or leave empty to skip: ").strip()
            if manual:
                chosen = manual

        if chosen:
            if not migrate_data(chosen, engine):
                print("\n⚠ Data migration failed, but schema is ready")
        else:
            print("ℹ Skipped data migration")
    else:
        print("ℹ Skipped data migration")

    print("\n" + "=" * 60)
    print("✓ Migration completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start your app: uvicorn app.main:app --reload")
    print("2. Test API: curl http://localhost:8000/api/v1/health")
    print("3. View tables in Supabase dashboard")


if __name__ == "__main__":
    main()
