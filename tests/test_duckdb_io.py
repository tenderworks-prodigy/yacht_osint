import pandas as pd

import duckdb
from src.persist import duckdb_io


def test_duckdb_round_trip(tmp_path):
    db = tmp_path / "test.duckdb"
    df = pd.DataFrame([{"name": "B", "length_m": 2.0}])
    duckdb_io.run(df, db)
    con = duckdb.connect(str(db))
    out = con.execute("SELECT name, length_m FROM yachts").fetch_df()
    assert out.equals(df)
    con.close()
