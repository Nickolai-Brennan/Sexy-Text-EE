from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.graphql.schema import schema
from app.graphql.resolvers import get_context
from app.db.session import engine
from app.db.base import Base

app = FastAPI(title="editor-api")

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
async def health():
    return {"ok": True}

# Dev convenience: auto-create tables on startup (replace with Alembic later)
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
