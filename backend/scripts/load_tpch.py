"""Generate a TPC-H-derived dataset with DuckDB's built-in dbgen and load it into PostgreSQL.

    python scripts\\load_tpch.py --sf 1          # ~1 GB raw, ~4 GB in PostgreSQL with keys
    python scripts\\load_tpch.py --sf 0.1 --schema tpch_dev

No C compiler is needed: DuckDB ships the reference data generator (``INSTALL tpch``),
which produces the same deterministic tables as the TPC's dbgen for a given scale factor.
The data is loaded into its own schema (default ``tpch``) in the GreenCode database, with
the primary and foreign keys the TPC-H specification permits, then ANALYZEd.

The TPC allows the tools to be used for non-commercial research; results must be described
as "TPC-H-derived", never as an official TPC-H result.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402

from app.config import get_settings  # noqa: E402

TABLES = ["region", "nation", "supplier", "part", "partsupp", "customer", "orders", "lineitem"]

DDL = """
CREATE TABLE {s}.region   (r_regionkey INTEGER NOT NULL, r_name CHAR(25) NOT NULL, r_comment VARCHAR(152));
CREATE TABLE {s}.nation   (n_nationkey INTEGER NOT NULL, n_name CHAR(25) NOT NULL, n_regionkey INTEGER NOT NULL, n_comment VARCHAR(152));
CREATE TABLE {s}.supplier (s_suppkey INTEGER NOT NULL, s_name CHAR(25) NOT NULL, s_address VARCHAR(40) NOT NULL,
                           s_nationkey INTEGER NOT NULL, s_phone CHAR(15) NOT NULL, s_acctbal NUMERIC(15,2) NOT NULL, s_comment VARCHAR(101) NOT NULL);
CREATE TABLE {s}.part     (p_partkey INTEGER NOT NULL, p_name VARCHAR(55) NOT NULL, p_mfgr CHAR(25) NOT NULL, p_brand CHAR(10) NOT NULL,
                           p_type VARCHAR(25) NOT NULL, p_size INTEGER NOT NULL, p_container CHAR(10) NOT NULL,
                           p_retailprice NUMERIC(15,2) NOT NULL, p_comment VARCHAR(23) NOT NULL);
CREATE TABLE {s}.partsupp (ps_partkey INTEGER NOT NULL, ps_suppkey INTEGER NOT NULL, ps_availqty INTEGER NOT NULL,
                           ps_supplycost NUMERIC(15,2) NOT NULL, ps_comment VARCHAR(199) NOT NULL);
CREATE TABLE {s}.customer (c_custkey INTEGER NOT NULL, c_name VARCHAR(25) NOT NULL, c_address VARCHAR(40) NOT NULL,
                           c_nationkey INTEGER NOT NULL, c_phone CHAR(15) NOT NULL, c_acctbal NUMERIC(15,2) NOT NULL,
                           c_mktsegment CHAR(10) NOT NULL, c_comment VARCHAR(117) NOT NULL);
CREATE TABLE {s}.orders   (o_orderkey INTEGER NOT NULL, o_custkey INTEGER NOT NULL, o_orderstatus CHAR(1) NOT NULL,
                           o_totalprice NUMERIC(15,2) NOT NULL, o_orderdate DATE NOT NULL, o_orderpriority CHAR(15) NOT NULL,
                           o_clerk CHAR(15) NOT NULL, o_shippriority INTEGER NOT NULL, o_comment VARCHAR(79) NOT NULL);
CREATE TABLE {s}.lineitem (l_orderkey INTEGER NOT NULL, l_partkey INTEGER NOT NULL, l_suppkey INTEGER NOT NULL,
                           l_linenumber INTEGER NOT NULL, l_quantity NUMERIC(15,2) NOT NULL, l_extendedprice NUMERIC(15,2) NOT NULL,
                           l_discount NUMERIC(15,2) NOT NULL, l_tax NUMERIC(15,2) NOT NULL, l_returnflag CHAR(1) NOT NULL,
                           l_linestatus CHAR(1) NOT NULL, l_shipdate DATE NOT NULL, l_commitdate DATE NOT NULL,
                           l_receiptdate DATE NOT NULL, l_shipinstruct CHAR(25) NOT NULL, l_shipmode CHAR(10) NOT NULL,
                           l_comment VARCHAR(44) NOT NULL);
"""

# Keys the specification allows (clause 1.4): primary keys, foreign keys and the composite key on lineitem.
KEYS = """
ALTER TABLE {s}.region   ADD PRIMARY KEY (r_regionkey);
ALTER TABLE {s}.nation   ADD PRIMARY KEY (n_nationkey);
ALTER TABLE {s}.supplier ADD PRIMARY KEY (s_suppkey);
ALTER TABLE {s}.part     ADD PRIMARY KEY (p_partkey);
ALTER TABLE {s}.partsupp ADD PRIMARY KEY (ps_partkey, ps_suppkey);
ALTER TABLE {s}.customer ADD PRIMARY KEY (c_custkey);
ALTER TABLE {s}.orders   ADD PRIMARY KEY (o_orderkey);
ALTER TABLE {s}.lineitem ADD PRIMARY KEY (l_orderkey, l_linenumber);
ALTER TABLE {s}.nation   ADD FOREIGN KEY (n_regionkey) REFERENCES {s}.region (r_regionkey);
ALTER TABLE {s}.supplier ADD FOREIGN KEY (s_nationkey) REFERENCES {s}.nation (n_nationkey);
ALTER TABLE {s}.customer ADD FOREIGN KEY (c_nationkey) REFERENCES {s}.nation (n_nationkey);
ALTER TABLE {s}.partsupp ADD FOREIGN KEY (ps_partkey) REFERENCES {s}.part (p_partkey);
ALTER TABLE {s}.partsupp ADD FOREIGN KEY (ps_suppkey) REFERENCES {s}.supplier (s_suppkey);
ALTER TABLE {s}.orders   ADD FOREIGN KEY (o_custkey) REFERENCES {s}.customer (c_custkey);
ALTER TABLE {s}.lineitem ADD FOREIGN KEY (l_orderkey) REFERENCES {s}.orders (o_orderkey);
ALTER TABLE {s}.lineitem ADD FOREIGN KEY (l_partkey, l_suppkey) REFERENCES {s}.partsupp (ps_partkey, ps_suppkey);
CREATE INDEX ON {s}.lineitem (l_shipdate);
CREATE INDEX ON {s}.lineitem (l_partkey);
CREATE INDEX ON {s}.lineitem (l_suppkey);
CREATE INDEX ON {s}.orders (o_orderdate);
CREATE INDEX ON {s}.orders (o_custkey);
CREATE INDEX ON {s}.partsupp (ps_suppkey);
CREATE INDEX ON {s}.customer (c_nationkey);
CREATE INDEX ON {s}.supplier (s_nationkey);
"""


def generate(sf: float, outdir: Path) -> dict[str, int]:
    try:
        import duckdb  # type: ignore
    except ImportError:
        sys.exit("duckdb is required to generate the data:  pip install --user duckdb")
    con = duckdb.connect()
    con.execute("INSTALL tpch; LOAD tpch;")
    t0 = time.perf_counter()
    con.execute(f"CALL dbgen(sf = {sf});")
    print(f"  dbgen(sf={sf}) in {time.perf_counter() - t0:.1f}s")
    counts = {}
    for t in TABLES:
        path = outdir / f"{t}.csv"
        con.execute(f"COPY {t} TO '{path.as_posix()}' (FORMAT CSV, HEADER false, DELIMITER '|')")
        counts[t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  {t:9s} {counts[t]:>10,d} rows -> {path.name}")
    con.close()
    return counts


def load(schema: str, outdir: Path, dsn: str) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        conn.execute(f"CREATE SCHEMA {schema}")
        conn.execute(DDL.format(s=schema))
        for t in TABLES:
            t0 = time.perf_counter()
            with conn.cursor() as cur, open(outdir / f"{t}.csv", "rb") as fh:
                with cur.copy(f"COPY {schema}.{t} FROM STDIN (FORMAT CSV, DELIMITER '|')") as cp:
                    while chunk := fh.read(1 << 20):
                        cp.write(chunk)
            print(f"  loaded {t:9s} in {time.perf_counter() - t0:.1f}s")
        t0 = time.perf_counter()
        conn.execute(KEYS.format(s=schema))
        print(f"  keys and indexes in {time.perf_counter() - t0:.1f}s")
        t0 = time.perf_counter()
        for t in TABLES:
            conn.execute(f"ANALYZE {schema}.{t}")
        print(f"  ANALYZE in {time.perf_counter() - t0:.1f}s")
        size = conn.execute("SELECT pg_size_pretty(sum(pg_total_relation_size(c.oid))) FROM pg_class c "
                            "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s AND c.relkind = 'r'",
                            (schema,)).fetchone()[0]
        print(f"  schema {schema} on disk: {size}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sf", type=float, default=1.0, help="scale factor (1 = ~1 GB raw)")
    ap.add_argument("--schema", default=None, help="target schema (default: GREENCODE_TPCH_SCHEMA or 'tpch')")
    ap.add_argument("--keep-csv", action="store_true", help="keep the generated CSV files")
    args = ap.parse_args()
    settings = get_settings()
    schema = args.schema or settings.tpch_schema
    if not schema.replace("_", "").isalnum():
        sys.exit("schema name must be alphanumeric/underscore")
    tmp = Path(tempfile.mkdtemp(prefix="tpch_")) if not args.keep_csv else Path("tpch_csv"); tmp.mkdir(exist_ok=True)
    print(f"Generating TPC-H-derived data, sf={args.sf}, into schema '{schema}'")
    generate(args.sf, tmp)
    load(schema, tmp, settings.benchmark_database_url)
    if not args.keep_csv:
        for f in tmp.glob("*.csv"):
            f.unlink()
        tmp.rmdir()
    print("Done. Set GREENCODE_TPCH_SCHEMA=%s if you used a non-default schema." % schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
