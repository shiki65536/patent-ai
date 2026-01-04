from app.database import init_db, engine
from app.models import Base

print("Creating database tables...")
init_db()
print("✓ Database initialized successfully")

# Verify tables
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"✓ Tables created: {tables}")