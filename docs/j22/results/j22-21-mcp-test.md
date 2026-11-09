# J22-21 auto-ontology MCP 도구 시험 결과

- 일시: 2026-11-08 / 실행: Claude Code (Opus 5.5) / auto-ontology MCP 도구만 사용, 변경 없음
- 판정: 4번 PA 2016 질문은 **FAIL**, 5번 README Q1은 **PARTIAL**, readiness는 실제 동작과 모순됨
  - 정정(t2-claude): 4번의 기대값 588.80은 잘못 제시된 값이었음. 정답은 invoicelines 기준 2016년 PA 세금 포함 **1,473,304.05**(1,646줄)
  - 4번 답 11,587.98은 customertransactions의 유형1(송장) 458,236.47과 유형3(입금) -446,648.49를 더한 순합계, 즉 잔액이므로 여전히 오답
  - 5번 README Q1은 512.00을 반환함. 세금 제외 기대값과 일치하나 세금 포함 588.80은 제시하지 않음

## 1) check_readiness
| 항목 | 값 |
|---|---|
| ready | **false** |
| catalog_present | true (DB: wideworldimporters) |
| semantic_layer_built | true |
| can_execute_sql | **false** |
| blocker | "No database connection is configured…" |

⚠ 모순: 4번 ask_question은 SQL을 실행해 행 1개를 반환함 → readiness의 연결 판정이 틀렸거나, 다른 경로로 연결이 확인되고 있음. 원인 조사가 필요함.

## 2) search_terms 'customer' (전체 6건 중 상위 5건, 모두 certification=pending)
| # | Term | 컬럼 속성 수 |
|---|---|---|
| 1 | Archived Customer | 21 |
| 2 | Customer | 22 |
| 3 | Customer Category | 4 |
| 4 | Customer Category (…customercategories_archive) | 4 |
| 5 | Customer Transaction | 9 |

## 3) check_answerable
- coverage **0.75**, uncovered_entities 없음
- 후보: Customer ID, Customer Transaction.Transaction Amount, Transaction Date, Invoice.Invoice Date 등
- 주(State)·도시 관련 후보가 하나도 없음 → Pennsylvania 필터를 받쳐 줄 근거가 약함

## 4) ask_question
- 소요 시간: **약 51.7초**
- 행 수: 1 (truncated=false)
- 답: **11,587.98** (정정된 정답: 세금 포함 1,473,304.05) → **불일치** (customertransactions 잔액을 합산함)

```sql
SELECT COALESCE(SUM(ct.transactionamount), 0) AS total_sales_including_tax
FROM wideworldimporters.sales.customertransactions AS ct
INNER JOIN wideworldimporters.sales.customers AS c ON ct.customerid = c.customerid
INNER JOIN wideworldimporters.application.cities AS ci ON c.deliverycityid = ci.cityid
INNER JOIN wideworldimporters.application.stateprovinces AS sp ON ci.stateprovinceid = sp.stateprovinceid
WHERE sp.stateprovincename = 'Pennsylvania'
  AND ct.transactiondate >= DATE '2016-01-01'
  AND ct.transactiondate <= DATE '2016-12-31'
```

### 기대 경로와의 차이
| 구분 | 기대 | 실제 |
|---|---|---|
| 매출 원천 | invoicelines → invoices | **customertransactions** |
| 고객→지역 | customers.deliverycityid → cities → stateprovinces | 동일 ✅ |
| 금액 | invoicelines 세금 포함 금액 합계 | transactionamount를 거래 유형 구분 없이 합산 |

- 지역 조인 경로는 맞았음
- 매출 원천을 잘못 골랐음. customertransactions에는 인보이스 외에 입금·조정 거래도 섞여 있는데, agent도 "거래 유형 필터 없음"을 가정으로 명시함
- reasoning을 보면 초기 candidate에 cities 테이블이 없어서, 처음에는 고객명 문자열(", PA)")을 매칭하고 people.lasteditedby 조인을 거친 뒤 재구성 단계에서야 cities를 찾았음

## 후속 조치 후보
1. readiness의 `can_execute_sql` 판정 로직과 실제 실행 경로가 왜 다른지 확인
2. "매출(Sales)" 용어를 invoicelines 기반 SQL attribute로 정의하고 certify
3. 주/도시(State, City) 용어가 candidate retrieval에 걸리도록 보강

## 5) README Q1
- 질문: "What was revenue for the USB food flash drive - sushi roll in Pennsylvania in June 2015?"
- 기대값: 세금 포함 $588.80 / 세금 제외 $512.00 (송장 라인 3줄)
- 소요 시간: **약 32.0초**
- 결과 행 수: 1 (집계 결과 1행이며, 내부 라인이 3줄인지는 확인하지 못함. raw DB 조회는 시험 범위 밖)
- 답: **512.00** → 세금 제외 기대값과 **일치** ✅. 세금 포함 588.80은 제시하지 않음
  - agent는 "질문에 tax-inclusive 요청이 없었으므로 세금 제외로 계산한다"는 가정을 명시함

```sql
SELECT COALESCE(SUM(il.quantity * il.unitprice), 0) AS revenue
FROM wideworldimporters.sales.invoicelines AS il
INNER JOIN wideworldimporters.warehouse.stockitems AS si ON il.stockitemid = si.stockitemid
INNER JOIN wideworldimporters.sales.invoices AS inv ON il.invoiceid = inv.invoiceid
INNER JOIN wideworldimporters.sales.customers AS c ON inv.customerid = c.customerid
INNER JOIN wideworldimporters.application.cities AS ci ON c.deliverycityid = ci.cityid
INNER JOIN wideworldimporters.application.stateprovinces AS sp ON ci.stateprovinceid = sp.stateprovinceid
WHERE si.stockitemname = 'USB food flash drive - sushi roll'
  AND sp.stateprovincename = 'Pennsylvania'
  AND inv.invoicedate >= DATE '2015-06-01'
  AND inv.invoicedate < DATE '2015-07-01'
```

| 항목 | 기대 | 실제 |
|---|---|---|
| 매출 원천 | invoicelines → invoices | 동일 ✅ |
| 고객→지역 | customers.deliverycityid → cities → stateprovinces | 동일 ✅ |
| 금액 | 세금 포함 588.80 (세금 제외 512.00) | quantity × unitprice = 512.00 (세금 제외만) |

- 4번과 달리 이번에는 매출 원천을 올바르게 골랐음
- 남은 이슈: "revenue"의 기본 정의(세금 포함인지 제외인지)를 glossary에 정의해 두지 않아 agent의 가정에 맡겨져 있음 → Revenue SQL attribute로 정의하고 certify해야 함
- 기타 가정: credit note를 제외하지 않음. 기준 날짜는 invoicedate
