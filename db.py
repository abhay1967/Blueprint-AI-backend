import os
import sqlalchemy
import databases
from sqlalchemy.dialects.postgresql import UUID

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy specific code
metadata = sqlalchemy.MetaData()

chat = sqlalchemy.Table(
    "chat",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Text, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.Text, nullable=False),

    sqlalchemy.Column("title", sqlalchemy.Text),
    sqlalchemy.Column("user_message", sqlalchemy.Text),
    sqlalchemy.Column("assistant_message", sqlalchemy.Text),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), server_default=sqlalchemy.func.now()),
)

database = databases.Database(DATABASE_URL, connect_args={"statement_cache_size": 0})
