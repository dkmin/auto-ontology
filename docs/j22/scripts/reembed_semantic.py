"""의미 계층 벡터(vdb.semantic_layer)를 현재 EMBED 모델로 DB별로 다시 만든다.

ingestion-service 컨테이너 안에서 실행한다 (컨테이너 env의 EMBED_* 사용).
DB마다 먼저 전부 임베딩하고, 행 수가 맞을 때만 기존 행을 지우고 새로 쓴다.
"""

from collections import defaultdict

from sqlalchemy import text

from auto_ontology.dal.session import get_engine
from auto_ontology.dal.terms import fetch_all_terms_and_attributes
from auto_ontology.semantic.embed import _build_rows
from auto_ontology.server.sql_attributes.service import _reembed_sql_attribute
from auto_ontology.utils.embedding import batch_embed, get_embed_params
from auto_ontology.vdb import get_semantic_vdb
from auto_ontology.vdb.records import write_embedded_rows

params = get_embed_params()
print("embed model:", params.model_name, "endpoint:", params.embed_invoke_url)

with get_engine().connect() as c:
    t2db = {
        r[0]: r[1]
        for r in c.execute(
            text(
                "select ct.id, cd.name from catalog_table ct "
                "join catalog_schema cs on cs.id = ct.schema_id "
                "join catalog_database cd on cd.id = cs.database_id"
            )
        )
    }
    term2db: dict[str, set[str]] = defaultdict(set)
    for term_id, table_id in c.execute(text("select term_id, table_id from table__term")):
        if table_id in t2db:
            term2db[term_id].add(t2db[table_id])
    sql_attrs = c.execute(
        text(
            "select distinct sa.id, cd.name from sql_attribute sa "
            "join sql_attribute__sql ss on ss.attribute_id = sa.id "
            "join sql_query__table sq on sq.sql_query_id = ss.sql_query_id "
            "join catalog_table ct on ct.id = sq.table_id "
            "join catalog_schema cs on cs.id = ct.schema_id "
            "join catalog_database cd on cd.id = cs.database_id"
        )
    ).fetchall()
    before = dict(
        c.execute(
            text("select database_name, count(*) from vdb.semantic_layer group by 1")
        ).fetchall()
    )

terms, attrs = fetch_all_terms_and_attributes()
attrs_by: dict[tuple[str, str], list[dict]] = defaultdict(list)
for a in attrs:
    db = t2db.get(a.get("table_id"))
    if db:
        attrs_by[(a.get("term_name") or "", db)].append(a)

rows_by_db: dict[str, list[dict]] = defaultdict(list)
for t in terms:
    for db in sorted(term2db.get(t.get("id"), set())):
        rows_by_db[db].extend(
            _build_rows(
                db,
                {
                    "name": t.get("name"),
                    "description": t.get("description") or "",
                    "synonyms": t.get("synonyms") or [],
                    "id": t.get("id"),
                    "schema_names": t.get("schema_names") or [],
                },
                attrs_by.get((t.get("name") or "", db), []),
            )
        )

sql_by_db: dict[str, list[str]] = defaultdict(list)
for attr_id, db in sql_attrs:
    sql_by_db[db].append(attr_id)

ONLY = set(__import__("os").environ.get("ONLY_DBS", "").split(",")) - {""}
for db, rows in sorted(rows_by_db.items()):
    if ONLY and db not in ONLY:
        continue
    df = batch_embed(rows, params)
    ok = [
        r for r in df.to_dict(orient="records") if (r.get("metadata") or {}).get("embedding")
    ]
    expected_before = before.get(db, 0) - len(sql_by_db.get(db, []))
    print(f"{db}: built={len(rows)} embedded={len(ok)} existing(non-sql)={expected_before}")
    if len(ok) != len(rows):
        raise SystemExit(f"{db}: embedding incomplete, nothing deleted")
    vdb = get_semantic_vdb(database_name=db)
    deleted = vdb.delete_by_database(db)
    written = write_embedded_rows(vdb, ok)
    for attr_id in sql_by_db.get(db, []):
        _reembed_sql_attribute(attr_id, db)
    print(f"{db}: deleted={len(deleted)} written={written} sql_reembedded={len(sql_by_db.get(db, []))}")

with get_engine().connect() as c:
    after = c.execute(
        text("select database_name, label, count(*) from vdb.semantic_layer group by 1, 2 order by 1, 2")
    ).fetchall()
print("after:", after)
