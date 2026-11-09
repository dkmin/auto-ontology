# J22 비교 시험: auto-ontology(A) vs dbhub-wwi 직접 조회(B)

- 일시: 2026-11-08 / 실행: Claude Code (Opus 5.5) / 변경 없음(읽기 전용)
- A = auto-ontology `ask_question` (의미 계층 경유)
- B = dbhub-wwi `search_objects` + `execute_sql` (wwi_ro로 조회, SQL은 직접 작성). B에서는 auto-ontology 도구를 쓰지 않음
- A의 Q1·Q2는 앞선 J22-21 시험 결과를 **재사용**함 ([[j22-21-mcp-test]])

## 요약 비교표
| 질문 | 방식 | 답 | 시간(대략) | 도구 호출 | 판정 |
|---|---|---|---|---|---|
| Q1 sushi roll PA 2015-06 | A (재사용) | 512.00 (세금 제외만) | 32초 | 1 | △ 세금 제외 값만 맞음 |
| Q1 | B | 포함 **588.80** / 제외 **512.00**, 3줄 | 아래 공통 참고 | 공통 | ✅ 정답 |
| Q2 PA 2016 세금 포함 | A (재사용) | 11,587.98 | 52초 | 1 | ❌ 오답 (customertransactions 잔액) |
| Q2 | B | 포함 **1,473,304.05** / 제외 **1,284,080.70**, 1,646줄 | 공통 | 공통 | ✅ 정답 |
| Q3 2015 상위 5개 상품 | A | 아래 표 (세금 포함) | 107초 | 1 | ✅ B와 완전히 일치 |
| Q3 | B | 아래 표 (세금 포함/제외) | 공통 | 공통 | 기준값 |

- B 공통 비용: 3개 질문에 걸쳐 `search_objects` 4회와 `execute_sql` 2회(본 쿼리 1회, 검증 1회)를 호출함. 탐색부터 결과까지 약 24초 걸렸으며, 내 추론 시간도 포함됨
- A의 시간은 `ask_question` 1회의 wall-clock임. Q2를 실행하기 전에 별도로 `check_readiness`와 `check_answerable`을 1회씩 호출했음

## Q1. "What was revenue for the USB food flash drive - sushi roll in Pennsylvania in June 2015?"
**A (재사용)**: 512.00. 계산식 `SUM(il.quantity * il.unitprice)`. 경로는 invoicelines → invoices → customers.deliverycityid → cities → stateprovinces로 정확했음. "revenue"를 세금 제외로 가정했고, 세금 포함 값은 제시하지 않음

**B**:
```sql
SELECT COUNT(*) lines, SUM(il.extendedprice) incl_tax, SUM(il.quantity*il.unitprice) excl_tax
FROM sales.invoicelines il
JOIN sales.invoices i ON i.invoiceid = il.invoiceid
JOIN warehouse.stockitems si ON si.stockitemid = il.stockitemid
JOIN sales.customers c ON c.customerid = i.customerid
JOIN application.cities ci ON ci.cityid = c.deliverycityid
JOIN application.stateprovinces sp ON sp.stateprovinceid = ci.stateprovinceid
WHERE si.stockitemname = 'USB food flash drive - sushi roll'
  AND sp.stateprovincename = 'Pennsylvania'
  AND i.invoicedate >= DATE '2015-06-01' AND i.invoicedate < DATE '2015-07-01';
-- 3 | 588.80 | 512.00
```

## Q2. "2016년 Pennsylvania 주 고객 매출(세금 포함)은?"
**A (재사용)**: 11,587.98 ❌. 고객→주 조인은 맞았지만 매출 원천을 `sales.customertransactions`로 잡고 `transactionamount`를 거래 유형 구분 없이 합산함. 결과는 송장(유형1) 458,236.47과 입금(유형3) -446,648.49의 순합계, 즉 잔액임

**B**: Q1과 같은 조인에서 stockitems 조건을 빼고 기간을 `2016-01-01 ≤ invoicedate < 2017-01-01`로 바꿈
→ 1,646줄 | 포함 **1,473,304.05** | 제외 **1,284,080.70** ✅

## Q3. "2015년 매출 상위 5개 상품과 각 매출액은?"
| 순위 | 상품 | A (세금 포함) | B 세금 포함 | B 세금 제외 |
|---|---|---|---|---|
| 1 | Air cushion machine (Blue) | 3,815,185.95 | 3,815,185.95 | 3,317,553.00 |
| 2 | 20 mm Double sided bubble wrap 50m | 2,406,996.00 | 2,406,996.00 | 2,093,040.00 |
| 3 | 32 mm Anti static bubble wrap (Blue) 50m | 2,332,890.00 | 2,332,890.00 | 2,028,600.00 |
| 4 | 20 mm Anti static bubble wrap (Blue) 50m | 2,315,502.00 | 2,315,502.00 | 2,013,480.00 |
| 5 | 10 mm Anti static bubble wrap (Blue) 50m | 2,313,432.00 | 2,313,432.00 | 2,011,680.00 |

- 두 방식의 결과가 **완전히 일치**함. 세금 제외로 순위를 매겨도 순서가 같음 (6위는 32 mm Double sided bubble wrap 50m, 2,242,408.00)
- A의 SQL은 `sales.invoices.invoicedate`를 쓰지 않음. 대신 `customertransactions`에서 송장별 `MIN(transactiondate)`를 구해 날짜로 사용하는 우회 경로를 택함
- B로 확인한 결과: 송장 날짜와 MIN(transactiondate)가 다른 송장 0건, customertransactions가 없는 송장 0건, credit note 0건. 따라서 이번 데이터에서는 우연히 같은 값이 나왔을 뿐, 경로 자체는 취약함

**B SQL**:
```sql
SELECT si.stockitemname, SUM(il.extendedprice) incl_tax, SUM(il.quantity*il.unitprice) excl_tax
FROM sales.invoicelines il
JOIN sales.invoices i ON i.invoiceid = il.invoiceid
JOIN warehouse.stockitems si ON si.stockitemid = il.stockitemid
WHERE i.invoicedate >= DATE '2015-01-01' AND i.invoicedate < DATE '2016-01-01'
GROUP BY si.stockitemname
ORDER BY incl_tax DESC, si.stockitemname
LIMIT 5;
```

## 결론
**정확도: B 3/3, A 1.5/3** (Q1은 절반만 맞음, Q2 오답, Q3 일치)

의미 계층이 **도움이 된 지점**
- 테이블·컬럼을 몰라도 자연어 질문 하나로 SQL과 답을 받을 수 있음. 호출도 질문당 1회로 끝남
- Q1·Q3에서는 FK 경로(customers.deliverycityid → cities → stateprovinces, invoicelines → stockitems)를 스스로 찾아냄
- reasoning에 가정(세금 포함/제외, credit note 미제외 등)을 명시해 주므로 사람이 검증할 수 있음

의미 계층이 **방해된 지점**
- **"매출" 정의가 없음**: Q1은 세금 제외, Q3는 세금 포함으로 계산해 질문마다 기준이 흔들림. Q2에서는 customertransactions까지 끌어들여 오답을 냄 → certify된 Revenue SQL attribute가 필요함
- **candidate retrieval 편향**: Customer Transaction 용어의 Transaction Amount, Transaction Date가 상위 후보로 올라와 매출·날짜 원천을 오염시킴 (Q2 오답, Q3의 우회 날짜 경로)
- **비용과 속도**: 질문당 32~107초가 걸림. B는 스키마 탐색을 한 번 하고 나면 3개 질문을 쿼리 한 번에 끝냄
- **readiness 신뢰도**: `can_execute_sql=false`라고 판정했지만 실제로는 SQL이 실행됨 (J22-21에서 확인)

**제안**: (1) Revenue(세금 포함은 extendedprice, 제외는 quantity×unitprice, 기준 날짜는 invoices.invoicedate)를 SQL attribute로 정의하고 certify (2) 매출 관련 질문에서 customertransactions의 retrieval 가중치를 낮추거나 "잔액/AR 전용" 설명을 추가 (3) 이 3문항을 회귀 평가셋으로 고정
