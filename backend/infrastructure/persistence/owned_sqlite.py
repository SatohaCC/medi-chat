"""A native connection closes every live cursor before releasing its OS handle."""

import sqlite3
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol, TypeVar, overload
from weakref import WeakSet


class SqliteSequence(Protocol):
    def __len__(self) -> int: ...
    def __getitem__(self, index: int, /) -> Any: ...


CursorType = TypeVar("CursorType", bound=sqlite3.Cursor)


class OwnedSqliteConnection(sqlite3.Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cursors: WeakSet[sqlite3.Cursor] = WeakSet()

    @overload
    def cursor(self, factory: None = None) -> sqlite3.Cursor: ...

    @overload
    def cursor(
        self, factory: Callable[[sqlite3.Connection], CursorType]
    ) -> CursorType: ...

    def cursor(
        self, factory: Callable[[sqlite3.Connection], sqlite3.Cursor] | None = None
    ) -> sqlite3.Cursor:
        result = super().cursor() if factory is None else super().cursor(factory)
        self._cursors.add(result)
        return result

    def execute(
        self, sql: str, parameters: SqliteSequence | Mapping[str, Any] = (), /
    ) -> sqlite3.Cursor:
        return self.cursor().execute(sql, parameters)

    def executemany(
        self, sql: str, parameters: Iterable[SqliteSequence | Mapping[str, Any]], /
    ) -> sqlite3.Cursor:
        return self.cursor().executemany(sql, parameters)

    def executescript(self, sql: str, /) -> sqlite3.Cursor:
        return self.cursor().executescript(sql)

    def close(self) -> None:
        for cursor in tuple(self._cursors):
            cursor.close()
        self._cursors.clear()
        super().close()
