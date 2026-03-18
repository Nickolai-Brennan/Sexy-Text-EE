from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from app.schema import schema
from app.db import Base, engine

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(GraphQLRouter(schema), prefix="/graphql")
