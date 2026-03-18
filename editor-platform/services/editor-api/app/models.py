import uuid
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db import Base

class Document(Base):
    __tablename__ = "documents"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_key = sa.Column(sa.Text, unique=True, nullable=False)

    content_md = sa.Column(sa.Text, nullable=False, default="")
    content_html = sa.Column(sa.Text, nullable=False, default="")
    content_text = sa.Column(sa.Text, nullable=False, default="")
    style_tokens = sa.Column(JSONB, nullable=False, default=dict)