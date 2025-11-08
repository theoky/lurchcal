def test_smoke_ro(ro_conn):
    cur = ro_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    assert isinstance(cur.fetchall(), list)


def test_smoke_rw(db_conn):
    db_conn.execute("PRAGMA user_version = 1")
    cur = db_conn.execute("PRAGMA user_version")
    assert cur.fetchone()[0] == 1
