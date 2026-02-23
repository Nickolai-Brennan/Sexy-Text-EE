import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid

class HtmlSnippet(Base):
    __tablename__ = "document_html_snippets"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    name = sa.Column(sa.Text, nullable=True)
    raw_html = sa.Column(sa.Text, nullable=False)
    sanitized_html = sa.Column(sa.Text, nullable=False)
    warnings = sa.Column(JSONB, nullable=False, default=list)

    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
