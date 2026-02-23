import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid

class Document(Base):
    __tablename__ = "documents"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_key = sa.Column(sa.Text, unique=True, nullable=False, index=True)
    title = sa.Column(sa.Text, nullable=True)

    content_md = sa.Column(sa.Text, nullable=False, default="")
    content_html = sa.Column(sa.Text, nullable=False, default="")
    content_text = sa.Column(sa.Text, nullable=False, default="")

    style_tokens = sa.Column(JSONB, nullable=False, default=dict)
    theme_key = sa.Column(sa.Text, nullable=False, default="default")

    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
