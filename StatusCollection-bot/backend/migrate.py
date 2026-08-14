from sqlalchemy import text

from database import engine

with engine.connect() as conn:
    result = conn.execute(text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'products'
          AND column_name = 'image_url'
        """
    ))

    if result.fetchone() is None:
        conn.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR"))
        conn.commit()
        print("Колонка image_url добавлена")
    else:
        print("Колонка image_url уже есть")