import sqlite3
import tempfile
from contextlib import closing

with tempfile.NamedTemporaryFile(suffix=".db") as f:
    with closing(sqlite3.connect(f.name)) as db:
        db.executescript(
            "create table usage(team text,cost real); "
            "insert into usage values('search',12.5),('agent',20.0),('search',7.5);"
        )
        rows = db.execute(
            "select team, round(sum(cost),2) total from usage group by team order by total desc"
        ).fetchall()
        print(rows)
