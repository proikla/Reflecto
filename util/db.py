import asyncio
from psycopg import AsyncConnection, sql
from APIKEYS import DBPASS
import logging
DBNAME = 'tg-helper'
USER = 'postgres'


DB_DSN = f"dbname={DBNAME} user={USER} password={DBPASS}"

logger = logging.getLogger(__name__)


class DBClient:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10):
        self._dsn = dsn
        self._pool: AsyncConnection | None = None
        self._min = min_size
        self._max = max_size

    async def init(self):
        # must be awaited once at startup
        self._pool = await AsyncConnection.connect(
            self._dsn
        )

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def exec(
            self,
        query: str,
        params=None
    ):
        async with await self._pool.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params=params)

                if query.strip().lower().startswith('select'):
                    return await cur.fetchall()

                await conn.commit()

    async def fetch_field(
        self,
        table: str = 'users',
        field: str = 'user_id',
        where_field: str = 'user_id',
        where_value='',
    ):
        """
        Return a single column value (or None) from a single-row query.
        """
        if not self._pool:
            raise RuntimeError(
                "DBClient not initialized; call await init() first")
        query = sql.SQL("SELECT {field} FROM {table} WHERE {wfield} = %s LIMIT 1").format(
            field=sql.Identifier(field),
            table=sql.Identifier(table),
            wfield=sql.Identifier(where_field),
        )
        async with await self._pool.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (where_value,))
                row = await cur.fetchone()
                logger.info(f"Executed {query}")
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
            raise RuntimeError(
                "DBClient not initialized; call await init() first")
        query = sql.SQL(
            "UPDATE {table} SET {field} = %s WHERE {wfield} = %s"
        ).format(
            table=sql.Identifier(table),
            field=sql.Identifier(field),
            wfield=sql.Identifier(where_field),
        )
        async with await self._pool.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (value, where_value))
                logger.info(f"Executed {query}")
                await conn.commit()

    async def upsert_field(
        self,
        table: str,
        key_field: str,
        key_value: str,
        target_field: str,
        target_value: str
    ) -> None:
        q = sql.SQL("""
INSERT INTO {tbl} ({kf}, {tf})
VALUES (%s, %s)
ON CONFLICT ({kf})
DO UPDATE SET {tf} = EXCLUDED.{tf}
""").format(tbl=sql.Identifier(table), kf=sql.Identifier(key_field), tf=sql.Identifier(target_field))
        async with await self._pool.connect(self._dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(q, (key_value, target_value))
                await conn.commit()


db_client = DBClient(DB_DSN)

# async def get_user_context(user_id):
#     "Return chat context from the db."
#     async with await psycopg.AsyncConnection.connect(f"dbname={DBNAME} user={USER} password={DBPASS}") as conn:
#         async with conn.cursor() as cur:
#             await cur.execute(
#                 "SELECT evaluation FROM chats WHERE chat_with_id=%s",
#                 (user_id,)
#             )
#             fetch = await cur.fetchone()
#             if fetch:
#                 evaluation, = fetch
#             else:
#                 evaluation = None

#             return evaluation
#     return None

# async def update_user_timezone(chat_id) -> None:


# # ! redundant
# async def does_chat_have_context(chat_id) -> bool:
#     "Return `True` if `chat_id` has context in the db. Return `False` otherwise"
#     raise DeprecationWarning()
#     async with await psycopg.AsyncConnection.connect(f"dbname={DBNAME} user={USER} password={DBPASS}") as conn:
#         async with conn.cursor() as cur:
#             await cur.execute(
#                 "SELECT EXISTS(SELECT 1 FROM chats WHERE chat_with_id = %s)",
#                 (chat_id,)
#             )
#             exists, = await cur.fetchone()
#             return exists


# async def dump_context_data(chat_name, json_data, table='users') -> bool:
#     "dump context data into the database and return True if successful"
#     async with await psycopg.AsyncConnection.connect(f"dbname={DBNAME} user={USER} password={DBPASS}") as conn:
#         async with conn.cursor() as cur:
#             query = sql.SQL("INSERT INTO {} (chat_with_id, evaluation) VALUES (%s, %s)").format(
#                 sql.Identifier(table)
#             )
#             await cur.execute(query, [chat_name, json.dumps(json_data)])
#         await conn.commit()
#         return True


# async def main():
#     eval = await get_user_context(483273070)
#     print(eval)


# # testing
# if __name__ == '__main__':
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
#     asyncio.run(main())
