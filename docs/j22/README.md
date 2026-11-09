# J22 auto-ontology 로컬 가동 시험 정리

- 기간: 2026-11-07 ~ 2026-11-09
- 작업 관리: Asana 프로젝트 "J22-auto-ontology 로컬 가동 시험" (SSoT)
- 브랜치: `chore/j22-local-patches` (로컬 가동용 패치와 이 문서)

## TL;DR

auto-ontology를 맥북(M1) 한 대에서 띄워, 영어 샘플 DB(Wide World Importers)와 한국어 전자상거래 DB(`ecommerce_ko`)로 시험했습니다.

| 항목 | 결과 |
|---|---|
| 한국어 10문항 정확도 | 7.5 → 8.5 → **9.0** / 10 |
| `ask_question` 응답 시간 | 평균 41.1초 (51회), 범위 20~98초 |
| 같은 질문 재질의 | 캐시 없음, 매번 전체 파이프라인 재실행 |
| 가장 효과가 큰 개선 | 한국어 설명과 동의어, 인증한 매출 정의 SQL 속성 |

정확도는 의미 계층(설명, 동의어, 지표 정의)을 손볼수록 올라갔습니다. 반면 속도는 LLM을 여러 번 차례로 호출하는 구조 때문에 수십 초가 기본입니다. 자주 쓰는 질문은 SQL을 저장해 두는 방식이 필요합니다(J22-34).

## 구성

| 구성 요소 | 위치 | 비고 |
|---|---|---|
| 웹 UI | 127.0.0.1:3100 | 3000번은 다른 서비스가 사용 중 |
| API, ingestion | 127.0.0.1:3001, 3002 | 외부에 열지 않음 |
| MCP 서버 | 127.0.0.1:3003 | Claude Code에 로컬 범위로 등록 |
| Postgres | `auto_ontology`, `ecommerce_ko` DB | 의미 계층과 벡터(`vdb`, `halfvec(2048)`) |
| LLM | `claude-sonnet-5-5` | REASONING, NON_REASONING 모두 |
| 임베딩 | KURE-v3 (2048차원), m4-air의 MPS | M1에서 SSH 터널(Tailscale)로 3004번 연결 |

- 포트를 127.0.0.1에만 여는 설정은 [docker-compose.override.example.yml](scripts/docker-compose.override.example.yml)에 있습니다.
- KURE-v3를 옮긴 이유: M1(16GB)에서 Docker와 함께 돌리면 load가 10을 넘었습니다. m4-air로 옮긴 뒤 6.6으로 내려갔습니다.

## 시험 결과

| 시험 | 조건 | 결과 | 문서 |
|---|---|---|---|
| J22-21 MCP 도구 | WWI, 기본 설정 | Q4 오답, `check_readiness`와 실제 동작이 모순 | [j22-21-mcp-test](results/j22-21-mcp-test.md) |
| A/B 비교 | auto-ontology 대 SQL 직접 작성 | A는 정답 1, 부분 정답 1, 오답 1, 직접 작성은 모두 정답 | [j22-dbhub-compare](results/j22-dbhub-compare.md) |
| J22-33.2 | `ecommerce_ko`, 정의를 질문에 명시 | 3/3 | [j22-ecom-A](results/j22-ecom-A.md) |
| J22-33.3 | 10문항, NVIDIA 임베딩, 영어 설명 | 7.5/10 | [j22-ecom-A10](results/j22-ecom-A10.md) |
| J22-33.4 | KURE-v3, 한국어 설명과 동의어 | 8.5/10 | [j22-ecom-A10-kure](results/j22-ecom-A10-kure.md) |
| J22-33.5 | 매출 SQL 속성 인증, 집계 뷰 주의 문구 | 9.0/10 | [j22-ecom-A10-rev](results/j22-ecom-A10-rev.md) |

- 정답 SQL은 [ecom-gt.sql](scripts/ecom-gt.sql)에 있습니다.
- 33.5에서 N7(대분류 카테고리별 매출)은 오히려 나빠졌습니다. 카테고리 이름이 중복되는데(AMD, 무선) id 대신 이름으로 조인했기 때문입니다.

## 의미 계층에 넣은 것

공식 매출 정의는 SQL 속성 두 개로 등록하고 인증했습니다.

| SQL 속성 | 연결 용어 | 정의 |
|---|---|---|
| 매출 (Revenue) | Order | `orders.total_amount` 합계, 취소·반품·반품 요청 제외, `ordered_at` 기준 |
| 상품 매출 (Product Revenue) | Order Item | `order_items.subtotal` 합계, 같은 제외 조건, `product_id` 단위 |

> [!WARNING]
> 이 정의는 시험 정답에 맞춰 넣은 것이며, 업무 규칙으로 확정된 것은 아닙니다. 반품 요청을 제외할지와 기간 기준(주문일, 구매 확정일)은 DK가 결정해야 합니다.

화면에서 확인하려면 웹 UI의 `/terms`에서 용어를 검색합니다. 검색은 용어 이름(예: `Order`)으로만 됩니다.

## 스크립트

```text
scripts/
├── kure_server.py        KURE-v3 임베딩 서버 (OpenAI /v1/embeddings 호환, input_type → query/passage 접두사)
├── kure_check.py         모델 카드 예제 점수로 서버 검증 (기대값 약 [0.5386, 0.0152, -0.0211])
├── translate.py          ecommerce_ko 의미 계층 설명을 한국어로 (export → translate → apply)
├── reembed_semantic.py   vdb.semantic_layer를 현재 임베딩 모델로 DB별 재생성 (ingestion 컨테이너에서 실행)
├── revenue.py            매출 SQL 속성 2개 생성·인증, 집계 뷰 주의 문구 추가 (auto-ontology 컨테이너에서 실행)
├── ecom-gt.sql           10문항 정답 SQL
└── docker-compose.override.example.yml   포트를 127.0.0.1에만 여는 로컬 설정
```

비밀값은 모두 저장소 루트의 `.env`에서 읽고, 화면에 출력하지 않습니다.

## 재현 순서

1. `.env`를 손으로 옮깁니다. 키와 비밀번호가 들어 있어 git에 올리지 않습니다.
2. `scripts/docker-compose.override.example.yml`을 루트에 `docker-compose.override.yml`로 복사합니다.
3. 임베딩 서버를 띄웁니다. Apple Silicon 맥에서 `uv run`으로 `kure_server.py`를 3004번에 띄우고, `kure_check.py`로 점수를 확인합니다.
4. `.env`에 `EMBED_ENDPOINT=http://host.docker.internal:3004/v1`, `EMBED_MODEL=nlpai-lab/KURE-v3`를 넣고 스택을 올립니다.
5. 의미 계층을 옮깁니다. Postgres 덤프를 복원하거나 `/settings/import-export`로 가져옵니다.
6. 설명을 새로 만들었다면 `translate.py` → `revenue.py` → `reembed_semantic.py` 순서로 실행합니다.

`ecommerce_ko` 데이터는 [civilian7/sql-tutorial](https://github.com/civilian7/sql-tutorial)의 생성기로 만들었습니다. 생성기 코드는 MIT이고 문서는 CC BY-NC-SA입니다. 데이터는 이 저장소에 넣지 않았습니다.

## 남은 일

| Asana | 할 일 | 상태 |
|---|---|---|
| J22-34 | 자주 쓰는 질문의 SQL 저장 (질문 로그 → SQL로 묶기 → `custom_analysis`) | ⬜ 미착수 |
| J22-06.5 | KURE 서버와 터널 자동 재시작 (현재 수동 nohup) | ⬜ 미착수 |
| J22-13 | Semantic Compilation 켜기 (한국어 설명 덮어쓰기 확인 뒤) | ⚠️ 현재 꺼 둠 |
| J22-32 | 개발 DB(smfkr) 읽기 전용 연결 | ⬜ DK 승인 필요 |
| J22-41, 42 | 기존 온톨로지와 비교, 도입 여부 결정 | ⬜ DK 결정 |

질문 로그는 `frontend.conversation_analytics`에 질문, SQL, 응답 시각이 자동으로 쌓입니다. J22-34는 이 로그에서 시작합니다.
