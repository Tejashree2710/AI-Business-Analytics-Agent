
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from backend.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)

    filename = Column(String(255), nullable=False)

    file_type = Column(String(50), nullable=False)

    chunk_index = Column(Integer, nullable=False)

    content = Column(Text, nullable=False)

    embedding = Column(Vector(768), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
