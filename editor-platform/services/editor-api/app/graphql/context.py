from strawberry.fastapi import BaseContext
from sqlalchemy.ext.asyncio import AsyncSession

class GraphQLContext(BaseContext):
    db: AsyncSession
