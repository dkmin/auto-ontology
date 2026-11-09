# J22 한국어 DB 시험 3: ecommerce_ko 10문항 재시험 (KURE-v3 임베딩, 한국어 설명)

- 일시: 2026-11-08 / 실행: Claude Code (Opus 5.5) / 읽기 전용
- 조건: 임베딩 모델을 KURE-v3로 바꾸고, ecommerce_ko 의미 계층 설명을 한국어로 바꾼 뒤 실행함 (변경 자체는 t2-claude가 했으며, 브리프에 적힌 내용 그대로 옮김)
- 사용 도구: `ask_question`만 사용. U1부터 N10까지 순서대로 1회씩 호출했고, 이전 호출이 끝난 뒤에 다음 호출을 보냄
- DB 지정: `ask_question`에 database 인자가 없어서 지정하지 않음. 생성된 SQL은 모두 `ecommerce_ko.public.*`를 참조함
- 정답 판정을 하지 않았고, 이전 결과와도 비교하지 않음 (브리프 지시)
- wall-clock은 호출 앞뒤 타임스탬프의 차이이며, 수백 ms 정도의 오버헤드가 포함됨

## 요약
| # | 질문 | wall-clock | 오류 | 행 수 |
|---|---|---|---|---|
| U1 | 2024년 월별 매출액 | 24.5초 | 없음 | 12 |
| U2 | 2024년 매출 상위 5개 상품 | 61.9초 | 없음 | 5 |
| U3 | 2024년 서울 지역 매출 | 29.5초 | 없음 | 1 |
| N4 | 2024년 반품 사유별 건수 | 26.0초 | 없음 | 6 |
| N5 | 등급별 고객 수와 1인당 평균 매출 | 59.3초 | 없음 | 4 |
| N6 | 2024년 결제 수단별 결제 완료 금액 | 25.7초 | 없음 | 6 |
| N7 | 대분류 카테고리별 2024년 매출 | 68.5초 | 없음 | 18 |
| N8 | 리뷰 10건 이상, 평균 별점 상위 5개 | 31.6초 | 없음 | 5 |
| N9 | 재고 0인 판매 중 상품 수 | 29.2초 | 없음 | 1 |
| N10 | 2024년 택배사별 평균 배송 소요일 | 24.9초 | 없음 | 4 |

---

## U1. 2024년 월별 매출액은?
| month | revenue |
|---|---|
| 2024-01-01 | 301075320 |
| 2024-02-01 | 426177449 |
| 2024-03-01 | 536322767 |
| 2024-04-01 | 470154081 |
| 2024-05-01 | 459724596 |
| 2024-06-01 | 377040302 |
| 2024-07-01 | 363944597 |
| 2024-08-01 | 416494161 |
| 2024-09-01 | 560283059 |
| 2024-10-01 | 435107926 |
| 2024-11-01 | 567534472 |
| 2024-12-01 | 432917981 |

```sql
SELECT m.month, m.revenue
FROM ecommerce_ko.public.mv_monthly_sales AS m
WHERE m.month >= DATE '2024-01-01' AND m.month < DATE '2025-01-01'
ORDER BY m.month;
```
- 가정: 사전 집계된 `mv_monthly_sales`에 월마다 한 행이 있다고 보고 추가 집계 없이 그대로 조회함. NULL 매출은 그대로 둠

## U2. 2024년 매출 상위 5개 상품은?
| 순위 | name |
|---|---|
| 1 | Razer Blade 18 블랙 |
| 2 | Razer Blade 16 실버 |
| 3 | MacBook Air 15 M3 실버 |
| 4 | ASUS Dual RTX 4060 Ti 블랙 |
| 5 | ASUS Dual RTX 5070 Ti 실버 |

(매출액 컬럼은 출력하지 않고 상품명만 반환함)

```sql
SELECT p.name
FROM ecommerce_ko.public.order_items AS oi
INNER JOIN ecommerce_ko.public.products AS p ON oi.product_id = p.id
INNER JOIN ecommerce_ko.public.orders AS o ON oi.order_id = o.id
WHERE o.created_at >= '2024-01-01' AND o.created_at < '2025-01-01'
GROUP BY p.id, p.name
ORDER BY SUM(oi.subtotal) DESC, p.id ASC
LIMIT 5;
```
- 가정:
  - orders 테이블의 날짜 컬럼을 확인하지 못해서, 다른 테이블의 명명 규칙을 따라 `created_at`이 있다고 추정함
  - 매출은 `SUM(order_items.subtotal)`(할인 반영)로 봄
  - 질문에 상태 조건이 없고 status 컬럼도 보이지 않아서 주문 상태로 거르지 않음
  - 동점이면 상품 id 순으로 정렬함. 상위 N개를 묻는 질문이라 상품명만 출력함

## U3. 2024년 서울 지역 매출은?
| seoul_revenue_2024 |
|---|
| 419877154 |

```sql
SELECT COALESCE(SUM(v.total_amount), 0) AS seoul_revenue_2024
FROM ecommerce_ko.public.v_order_detail AS v
WHERE v.delivery_address LIKE '서울%'
  AND v.ordered_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND v.ordered_at < TIMESTAMP '2025-01-01 00:00:00'
```
- 가정: 서울은 `delivery_address`가 '서울'로 시작하는 주소로 판별함('서울특별시…'). 매출은 `SUM(total_amount)`임. 질문에 제외 조건이 없으므로 모든 주문 상태를 포함함

## N4. 2024년에 접수된 반품을 사유별로 건수를 세어줘.
| reason | return_count |
|---|---|
| change_of_mind | 58 |
| damaged_in_transit | 31 |
| defective | 27 |
| wrong_item | 18 |
| not_as_described | 14 |
| late_delivery | 7 |

```sql
SELECT r.reason, COUNT(r.id) AS return_count
FROM ecommerce_ko.public.returns AS r
WHERE r.requested_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND r.requested_at < TIMESTAMP '2025-01-01 00:00:00'
GROUP BY r.reason
ORDER BY return_count DESC, r.reason
```
- 가정:
  - "접수"를 `requested_at`으로 매핑함. 컬럼 설명에 "반품 접수일"이라고 되어 있고, glossary에서도 반품 접수로 정의되어 있어서임
  - 테이블 선택 단계에서는 `received_at`(입고)을 언급했지만, 최종 SQL에서는 `requested_at`을 택함
  - 건수가 0인 사유는 결과에 나오지 않음. 동점이면 사유명 순으로 정렬함

## N5. 고객 등급별 고객 수와, 2024년에 구매한 고객 기준 1인당 평균 매출은? 취소·반품(반품 요청 포함) 주문은 제외해.
| grade | customer_count | avg_revenue_per_buyer_2024 |
|---|---|---|
| BRONZE | 3859 | 1616041.9446022727 |
| SILVER | 479 | 2471140.446366782 |
| GOLD | 524 | 3232188.1639784947 |
| VIP | 368 | 6777027.6480263155 |

```sql
WITH customer_revenue AS (
  SELECT o.customer_id, SUM(o.total_amount) AS revenue_2024
  FROM ecommerce_ko.public.orders AS o
  WHERE o.ordered_at >= '2024-01-01'
    AND o.ordered_at < '2025-01-01'
    AND o.status NOT IN ('cancelled', 'returned', 'return_requested')
  GROUP BY o.customer_id
)
SELECT c.grade,
       COUNT(c.id) AS customer_count,
       CAST(SUM(cr.revenue_2024) AS NUMERIC) / NULLIF(COUNT(cr.customer_id), 0) AS avg_revenue_per_buyer_2024
FROM ecommerce_ko.public.customers AS c
LEFT JOIN customer_revenue AS cr ON c.id = cr.customer_id
GROUP BY c.grade
ORDER BY c.grade;
```
- 가정:
  - 고객 수는 비구매자를 포함한 등급별 전체 고객 수임
  - 평균 매출의 분모는 2024년 구매 고객 수이며, NULLIF로 0 나눗셈을 막음
  - 매출은 `orders.total_amount`이고, 2024년은 `ordered_at` 기준임
  - 취소·반품 제외는 주문 status로만 처리함. 결과는 등급 순으로 정렬함

## N6. 2024년 결제 수단별 결제 완료 금액 합계는?
| method | total_completed_amount |
|---|---|
| card | 2395888991 |
| kakao_pay | 1002822322 |
| naver_pay | 719061948 |
| bank_transfer | 483849949 |
| point | 261926968 |
| virtual_account | 250893342 |

```sql
SELECT p.method, SUM(p.amount) AS total_completed_amount
FROM ecommerce_ko.public.payments AS p
WHERE p.status = 'completed'
  AND p.paid_at >= '2024-01-01'
  AND p.paid_at < '2025-01-01'
GROUP BY p.method
ORDER BY total_completed_amount DESC;
```
- 가정:
  - 2024년은 `paid_at`(결제 완료 일시) 기준이며, `paid_at`이 NULL인 행은 제외됨
  - 완료된 결제가 없는 결제 수단은 결과에 나오지 않음
  - 합계 내림차순으로 정렬하며, 동률 처리 기준은 따로 두지 않음

## N7. 대분류 카테고리별 2024년 매출은? 취소·반품(반품 요청 포함) 주문은 제외해.
| top_category | revenue_2024 |
|---|---|
| 노트북 | 1383992100 |
| 모니터 | 719200400 |
| 그래픽카드 | 707730400 |
| 메인보드 | 395151200 |
| 스피커/헤드셋 | 229793600 |
| 저장장치 | 204264200 |
| 메모리(RAM) | 198989500 |
| 파워서플라이(PSU) | 191064500 |
| 키보드 | 183677100 |
| CPU | 144254400 |
| 케이스 | 139545800 |
| 마우스 | 137626300 |
| 네트워크 장비 | 135795600 |
| 데스크톱 PC | 123881700 |
| 쿨링 | 96034300 |
| 소프트웨어 | 52085100 |
| 프린터/스캐너 | 42745700 |
| UPS/전원 | 28697000 |

```sql
SELECT
  CASE WHEN c0.depth = 0 THEN c0.name WHEN c0.depth = 1 THEN c1.name ELSE c2.name END AS top_category,
  SUM(oi.subtotal) AS revenue_2024
FROM ecommerce_ko.public.orders AS o
INNER JOIN ecommerce_ko.public.order_items AS oi ON oi.order_id = o.id
INNER JOIN ecommerce_ko.public.products AS p ON oi.product_id = p.id
INNER JOIN ecommerce_ko.public.categories AS c0 ON p.category_id = c0.id
LEFT JOIN ecommerce_ko.public.categories AS c1 ON c0.parent_id = c1.id
LEFT JOIN ecommerce_ko.public.categories AS c2 ON c1.parent_id = c2.id
WHERE o.ordered_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND o.ordered_at < TIMESTAMP '2025-01-01 00:00:00'
  AND o.status NOT IN ('cancelled', 'returned', 'return_requested')
GROUP BY CASE WHEN c0.depth = 0 THEN c0.name WHEN c0.depth = 1 THEN c1.name ELSE c2.name END
ORDER BY revenue_2024 DESC, top_category
```
- 가정:
  - 대분류는 depth=0 카테고리로 봄. 하위 카테고리는 `parent_id`를 최대 2단계까지 따라 올라가 대분류로 묶음
  - 매출은 `SUM(order_items.subtotal)`임
  - 기간은 `ordered_at` 기준 2024년이며, 취소·반품·반품 요청 상태는 제외함
  - 매출이 없는 카테고리는 inner join 때문에 결과에서 빠짐. 동점이면 이름 순으로 정렬함

## N8. 리뷰가 10건 이상인 상품 중 평균 별점 상위 5개는?
| 순위 | name |
|---|---|
| 1 | LG 32UN880 에르고 화이트 |
| 2 | Arctic Liquid Freezer III Pro 420 A-RGB 실버 |
| 3 | Windows 11 Home 블랙 |
| 4 | WD Elements 2TB 블랙 |
| 5 | Dell XPS Desktop 8960 실버 |

(평균 별점과 리뷰 수 컬럼은 출력하지 않고 상품명만 반환함)

```sql
SELECT mpp.name
FROM ecommerce_ko.public.mv_product_performance AS mpp
WHERE mpp.review_count >= 10
ORDER BY mpp.avg_rating DESC NULLS LAST, mpp.review_count DESC, mpp.product_id ASC
LIMIT 5;
```
- 가정: `mv_product_performance`의 `review_count`와 `avg_rating`을 그대로 씀. 평균 별점이 같으면 리뷰 수가 많은 순, 그다음 상품 id 순으로 정렬함. 상품명만 출력하며, 안전장치로 `NULLS LAST`를 추가함

## N9. 현재 재고가 0인 판매 중 상품은 몇 개야?
| product_count |
|---|
| 1 |

```sql
SELECT COUNT(*) AS product_count
FROM ecommerce_ko.public.products AS p
WHERE p.stock_qty = 0
  AND p.is_active = TRUE
  AND p.discontinued_at IS NULL;
```
- 가정: 컬럼 설명을 근거로 "판매 중"을 `is_active = TRUE`이면서 `discontinued_at IS NULL`인 상품으로 봄. 재고 0은 `stock_qty = 0`과 정확히 일치하는 조건으로 판별함(`stock_qty`는 NOT NULL)

## N10. 2024년에 발송된 배송 건의 택배사별 평균 배송 소요일은?
| carrier | avg_delivery_days |
|---|---|
| 로젠택배 | 2.53 |
| 한진택배 | 2.52 |
| 우체국택배 | 2.48 |
| CJ대한통운 | 2.52 |

```sql
SELECT s.carrier, ROUND(CAST(AVG(EXTRACT(EPOCH FROM (s.delivered_at - s.shipped_at)) / 86400.0) AS NUMERIC), 2) AS avg_delivery_days
FROM ecommerce_ko.public.shipping AS s
WHERE s.shipped_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND s.shipped_at < TIMESTAMP '2025-01-01 00:00:00'
  AND s.delivered_at IS NOT NULL
GROUP BY s.carrier
ORDER BY s.carrier
```
- 가정: 소요일은 `delivered_at - shipped_at`을 일 단위(소수)로 환산한 값이며, 소수점 둘째 자리에서 반올림함. 기간은 `shipped_at` 기준 2024년임. `delivered_at`이 NULL인 미배송 건은 명시적으로 제외함. 결과는 택배사명 순으로 정렬함
