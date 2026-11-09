"""ecommerce_ko 의미 계층 설명을 한국어로 옮기는 스크립트.

1) export : 용어/속성 + 원본 DB 한국어 코멘트를 items.json으로 저장
2) translate : REASONING 모델(.env)로 한국어 설명·동의어 생성 → ko.json
3) apply : ko.json을 auto_ontology DB에 반영 (원문은 items.json에 보존)
비밀값은 출력하지 않는다.
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from openai import OpenAI

ENV = Path(__file__).resolve().parents[3] / ".env"  # 저장소 루트의 .env
OUT = Path(__file__).parent
DB = "ecommerce_ko"


def env() -> dict[str, str]:
    d = {}
    for line in ENV.read_text().splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m:
            d[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return d


E = env()


def conn(dbname: str) -> psycopg.Connection:
    return psycopg.connect(
        host="localhost",
        port=int(E.get("POSTGRES_PORT", "5432")),
        user=E.get("POSTGRES_USER", "postgres"),
        password=E["POSTGRES_PASSWORD"],
        dbname=dbname,
        autocommit=True,
    )


SCOPE = """
select ct.id, ct.name from catalog_table ct
join catalog_schema cs on cs.id = ct.schema_id
join catalog_database cd on cd.id = cs.database_id
where cd.name = %s
"""


def export() -> None:
    with conn("auto_ontology") as c:
        tables = dict(c.execute(SCOPE, [DB]).fetchall())
        terms = c.execute(
            """select distinct te.id, te.name, te.description, ct.name
               from term te join table__term tt on tt.term_id = te.id
               join catalog_table ct on ct.id = tt.table_id
               where ct.id = any(%s)""",
            [list(tables)],
        ).fetchall()
        attrs = c.execute(
            """select id, name, description, term_name, source_column, table_id
               from column_attribute where table_id = any(%s)""",
            [list(tables)],
        ).fetchall()
    with conn(DB) as c:
        tcom = dict(
            c.execute(
                "select relname, obj_description(oid) from pg_class "
                "where relnamespace = 'public'::regnamespace"
            ).fetchall()
        )
        ccom = {
            (r[0], r[1]): r[2]
            for r in c.execute(
                "select c.relname, a.attname, col_description(c.oid, a.attnum) "
                "from pg_attribute a join pg_class c on c.oid = a.attrelid "
                "where c.relnamespace = 'public'::regnamespace and a.attnum > 0"
            ).fetchall()
        }
    items = []
    for tid, name, desc, tname in terms:
        items.append(
            {"kind": "term", "id": tid, "name": name, "description": desc,
             "table": tname, "db_comment": tcom.get(tname)}
        )
    for aid, name, desc, term_name, src, table_id in attrs:
        tname = tables.get(table_id)
        col = (src or "").split(".")[-1]
        items.append(
            {"kind": "attr", "id": aid, "name": name, "description": desc,
             "term": term_name, "table": tname, "source_column": src,
             "db_comment": ccom.get((tname, col))}
        )
    (OUT / "items.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(f"exported {len(items)} items "
          f"({sum(i['kind'] == 'term' for i in items)} terms)")


SYSTEM = """너는 전자상거래 DB 의미 계층의 설명을 한국어로 옮기는 편집자다.
입력은 JSON 배열이다. 각 항목마다 아래 JSON 객체를 만들어 배열로만 답한다 (다른 글 금지).
- id: 그대로
- description_ko: 한국어 설명. 첫머리에 한국어 업무 명칭을 쓰고 마침표로 끝낸다.
  예) "반품 요청일시(반품 접수일). 고객이 반품을 요청한 시각. 물류센터 입고 일시(received_at)와 다르다."
  - db_comment(원본 DB의 한국어 코멘트)가 있으면 그 용어와 의미를 우선한다.
  - 영어 description에 있는 사실(값 목록, 형식, 조건)은 빠짐없이 옮긴다. 없는 사실을 지어내지 않는다.
  - 상태값·ENUM 값·컬럼명 같은 식별자는 영어 그대로 둔다.
- synonyms_ko: kind가 term일 때만. 사용자가 질문에 쓸 법한 한국어 동의어 2~5개 배열. attr이면 [].
"""


def translate() -> None:
    items = json.loads((OUT / "items.json").read_text())
    client = OpenAI(base_url=E["REASONING_ENDPOINT"], api_key=E["REASONING_API_KEY"])
    model = E["REASONING_MODEL"]
    batches = [items[i : i + 20] for i in range(0, len(items), 20)]

    def run(batch: list[dict]) -> list[dict]:
        payload = [
            {k: it.get(k) for k in
             ("id", "kind", "name", "description", "term", "table", "source_column", "db_comment")}
            for it in batch
        ]
        for attempt in range(3):
            r = client.chat.completions.create(
                model=model,
                max_tokens=8000,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
            text = r.choices[0].message.content or ""
            m = re.search(r"\[.*\]", text, re.S)
            try:
                out = json.loads(m.group(0)) if m else []
                if {o["id"] for o in out} == {p["id"] for p in payload}:
                    return out
            except Exception:
                pass
        raise RuntimeError(f"batch failed: {[p['id'] for p in payload][:3]}")

    with ThreadPoolExecutor(4) as ex:
        results = [o for chunk in ex.map(run, batches) for o in chunk]
    (OUT / "ko.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"translated {len(results)} items")


def apply() -> None:
    items = {i["id"]: i for i in json.loads((OUT / "items.json").read_text())}
    ko = json.loads((OUT / "ko.json").read_text())
    nt = na = 0
    with conn("auto_ontology") as c, c.transaction():
        for o in ko:
            it = items[o["id"]]
            if it["kind"] == "term":
                c.execute(
                    "update term set description = %s, synonyms = %s where id = %s",
                    [o["description_ko"], o.get("synonyms_ko") or [], o["id"]],
                )
                nt += 1
            else:
                c.execute(
                    "update column_attribute set description = %s where id = %s",
                    [o["description_ko"], o["id"]],
                )
                na += 1
    print(f"applied terms={nt} attrs={na}")


if __name__ == "__main__":
    {"export": export, "translate": translate, "apply": apply}[sys.argv[1]]()
