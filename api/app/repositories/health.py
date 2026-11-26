from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def pgvector_version(db: AsyncSession) -> str | None:
    return await db.scalar(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))


async def lightrag_table_names(db: AsyncSession) -> list[str]:
    table_rows = await db.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename LIKE 'lightrag%' "
            "ORDER BY tablename"
        )
    )
    return [row[0] for row in table_rows.fetchall()]
