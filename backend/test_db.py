from sqlalchemy import text
from backend.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        print("Database connected successfully!")
        print(result.fetchone()[0])

        vector = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        print("pgvector version:", vector.scalar())

except Exception as e:
    print("Database connection failed:", e)