# stdlib
import logging

# local
from APIKEYS import DBPASS

# third-party
from psycopg import AsyncConnection, sql

DBNAME = "tg-helper"
USER = "postgres"

DB_DSN = f"dbname={DBNAME} user={USER} password={DBPASS}"
logger = logging.getLogger(__name__)


class DBClient:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10):
        self._dsn = dsn
        self._pool: AsyncConnection | None = None
        self._min = min_size
        self._max = max_size

    async def init(self):  # ?
        # must be awaited once at startup
        self._pool = await AsyncConnection.connect(self._dsn)
        self._pool = await AsyncConnection.connect(self._dsn)

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def exec(
        self,
        query: str,
        params=None,
        fetchall=True,
    ):
        async with await self._pool.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params=params)

                if query.strip().lower().startswith("select"):
                    if fetchall:
                        return await cur.fetchall()
                    return await cur.fetchone()

                await conn.commit()

    async def fetch_field(
        self,
        table: str = "users",
        field: str = "user_id",
        where_field: str = "user_id",
        where_value="",
    ):
        """
        Return a single column value (or None) from a single-row query.
        """
        if not self._pool:
            raise RuntimeError("DBClient not initialized; call await init() first")
        query = sql.SQL(
            "SELECT {field} FROM {table} WHERE {wfield} = %s LIMIT 1"
        ).format(
            field=sql.Identifier(field),
            table=sql.Identifier(table),
            wfield=sql.Identifier(where_field),
        )
        async with await self._pool.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (where_value,))
                row = await cur.fetchone()
        return row[0] if row else None

    async def update_field(
        self,
        table: str,
        field: str,
        value,
        where_field: str,
        where_value,
    ) -> None:
        """
        Update a single column in a single row.
        """
        if not self._pool:
            logger.exception("DBCLIENT NOT INITIALIZED!")
            raise RuntimeError("DBClient not initialized; call await init() first")

        query = sql.SQL("UPDATE {table} SET {field} = %s WHERE {wfield} = %s").format(
            table=sql.Identifier(table),
            field=sql.Identifier(field),
            wfield=sql.Identifier(where_field),
        )
        async with await self._pool.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (value, where_value))
                await conn.commit()

    async def upsert_field(
        self,
        table: str,
        key_field: str,
        key_value: str,
        target_field: str,
        target_value: str,
    ) -> None:
        q = sql.SQL(
            """
INSERT INTO {tbl} ({kf}, {tf})
VALUES (%s, %s)
ON CONFLICT ({kf})
DO UPDATE SET {tf} = EXCLUDED.{tf}
        """
        ).format(
            tbl=sql.Identifier(table),
            kf=sql.Identifier(key_field),
            tf=sql.Identifier(target_field),
        )
        async with await self._pool.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(q, (key_value, target_value))
                await conn.commit()


db_client = DBClient(DB_DSN)
