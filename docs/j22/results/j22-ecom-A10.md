# J22 한국어 DB 시험 2: ecommerce_ko 10문항 (방식 A, ask_question)

- 일시: 2026-11-08 / 실행: Claude Code (Opus 5.5) / 읽기 전용
- 사용 도구: `ask_question`만 사용. U1부터 N10까지 순서대로 1회씩 호출했고, 이전 호출이 끝난 뒤에 다음 호출을 보냄
- DB 지정: `ask_question`에 database 인자가 없어서 지정하지 않음. 생성된 SQL은 모두 `ecommerce_ko.public.*`를 참조함
- 정답 판정은 하지 않음 (브리프 지시)
- wall-clock은 호출 앞뒤 타임스탬프의 차이이며, 수백 ms 정도의 오버헤드가 포함됨
- N7은 120초를 넘겨 클라이언트가 백그라운드 작업으로 전환함. 그래서 정확한 종료 시각을 알 수 없고, 범위로만 기록함

## 요약
| # | 질문 | wall-clock | 오류 | 행 수 |
|---|---|---|---|---|
| U1 | 2024년 월별 매출액 | 21.5초 | 없음 | 12 |
| U2 | 2024년 매출 상위 5개 상품 | 38.0초 | 없음 | 5 |
| U3 | 2024년 서울 지역 매출 | 29.5초 | 없음 | 1 |
| N4 | 2024년 반품 사유별 건수 | 24.0초 | 없음 | 6 |
| N5 | 등급별 고객 수와 1인당 평균 매출 | 34.2초 | 없음 | 4 |
| N6 | 2024년 결제 수단별 결제 완료 금액 | 23.9초 | 없음 | 6 |
| N7 | 대분류 카테고리별 2024년 매출 | 123~151초 | 오류는 없음. 120초 초과로 백그라운드 전환 | 18 |
| N8 | 리뷰 10건 이상, 평균 별점 상위 5개 | 25.0초 | 없음 | 5 |
| N9 | 재고 0인 판매 중 상품 수 | 24.8초 | 없음 | 1 |
| N10 | 2024년 택배사별 평균 배송 소요일 | 26.1초 | 없음 | 4 |

---

## U1. 2024년 월별 매출액은?
| month | monthly_revenue |
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
SELECT m.month, SUM(m.revenue) AS monthly_revenue
FROM ecommerce_ko.public.mv_monthly_sales AS m
WHERE m.month >= DATE '2024-01-01' AND m.month < DATE '2025-01-01'
GROUP BY m.month
ORDER BY m.month;
```
- 가정: 월별 매출액은 `mv_monthly_sales.revenue`를 그대로 쓴다고 봄. 뷰에 월마다 한 행이 있다고 가정했지만, 안전하게 SUM으로 다시 집계함. 데이터가 없는 달은 결과에서 빠짐

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
INNER JOIN ecommerce_ko.public.orders AS o ON oi.order_id = o.id
INNER JOIN ecommerce_ko.public.products AS p ON oi.product_id = p.id
WHERE o.ordered_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND o.ordered_at < TIMESTAMP '2025-01-01 00:00:00'
GROUP BY p.id, p.name
ORDER BY SUM(oi.subtotal) DESC, p.name
LIMIT 5;
```
- 가정:
  - orders 컬럼 목록을 받지 못해서 날짜 컬럼을 `ordered_at`으로 추정함
  - 매출은 `SUM(order_items.subtotal)`(할인 반영)로 봄
  - "status 컬럼이 없다"고 판단해 주문 상태로 거르지 않음
  - 동점이면 상품명 순으로 정렬함. 질문이 "어떤 상품"을 물었으므로 상품명만 출력함

## U3. 2024년 서울 지역 매출은?
| seoul_revenue_2024 |
|---|
| 419877154 |

```sql
SELECT COALESCE(SUM(o.total_amount), 0) AS seoul_revenue_2024
FROM ecommerce_ko.public.v_order_detail AS o
WHERE o.ordered_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND o.ordered_at < TIMESTAMP '2025-01-01 00:00:00'
  AND o.delivery_address LIKE '서울%'
```
- 가정:
  - 매출은 `SUM(total_amount)`로 봄
  - 질문에 취소·반품 제외 조건이 없으므로 모든 주문 상태를 포함함
  - 서울은 `delivery_address LIKE '서울%'`로 판별함
  - agent 스스로 "뷰가 주문 항목 단위 행이면 total_amount가 중복될 수 있으나, 메타데이터로 확인되지 않아 치명적으로 보지 않음"이라고 언급함

## N4. 2024년에 접수된 반품을 사유별로 건수를 세어줘.
| reason | return_count |
|---|---|
| change_of_mind | 21 |
| damaged_in_transit | 18 |
| wrong_item | 13 |
| defective | 12 |
| not_as_described | 9 |
| late_delivery | 2 |

```sql
SELECT r.reason, COUNT(*) AS return_count
FROM ecommerce_ko.public.returns AS r
WHERE r.received_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND r.received_at < TIMESTAMP '2025-01-01 00:00:00'
GROUP BY r.reason
ORDER BY return_count DESC, r.reason
```
- 가정: "접수"를 `received_at`(창고 입고 일시)으로 매핑함. `received_at`이 NULL인 행은 제외됨. 동점이면 사유명 순으로 정렬함

## N5. 고객 등급별 고객 수와, 2024년에 구매한 고객 기준 1인당 평균 매출은? 취소·반품(반품 요청 포함) 주문은 제외해.
| grade | customer_count | avg_revenue_per_purchasing_customer |
|---|---|---|
| BRONZE | 3859 | 1616041.9446022727 |
| SILVER | 479 | 2471140.446366782 |
| GOLD | 524 | 3232188.1639784947 |
| VIP | 368 | 6777027.6480263155 |

```sql
WITH cust_sales AS (
  SELECT o.customer_id, SUM(o.total_amount) AS cust_revenue
  FROM ecommerce_ko.public.orders AS o
  WHERE o.ordered_at >= TIMESTAMP '2024-01-01 00:00:00'
    AND o.ordered_at < TIMESTAMP '2025-01-01 00:00:00'
    AND o.status NOT IN ('cancelled', 'returned', 'return_requested')
  GROUP BY o.customer_id
)
SELECT c.grade,
       COUNT(c.id) AS customer_count,
       CAST(AVG(cs.cust_revenue) AS NUMERIC) AS avg_revenue_per_purchasing_customer
FROM ecommerce_ko.public.customers AS c
LEFT JOIN cust_sales AS cs ON cs.customer_id = c.id
GROUP BY c.grade
ORDER BY c.grade;
```
- 가정:
  - 고객 수는 구매 여부와 관계없이 등급별 전체 고객 수로 봄
  - 매출은 `orders.total_amount`의 합계임. 2024년은 `ordered_at` 기준임
  - 2024년에 구매가 없는 고객은 AVG 계산에서 NULL로 빠짐
  - 등급명 순으로 정렬함

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
  AND p.paid_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND p.paid_at < TIMESTAMP '2025-01-01 00:00:00'
GROUP BY p.method
ORDER BY total_completed_amount DESC
```
- 가정: 연도는 주문의 `completed_at`이 아니라 `paid_at`(결제 시각) 기준임. orders 조인은 필요 없다고 보고 생략함. `paid_at`이 NULL인 건은 제외됨

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
SELECT COALESCE(t.name, c.name) AS top_category, SUM(oi.subtotal) AS revenue_2024
FROM ecommerce_ko.public.order_items AS oi
INNER JOIN ecommerce_ko.public.orders AS o ON oi.order_id = o.id
INNER JOIN ecommerce_ko.public.products AS p ON oi.product_id = p.id
INNER JOIN ecommerce_ko.public.categories AS c ON p.category_id = c.id
LEFT JOIN ecommerce_ko.public.v_category_tree AS t ON c.parent_id = t.id
WHERE o.ordered_at >= '2024-01-01'
  AND o.ordered_at < '2025-01-01'
  AND o.status NOT IN ('cancelled', 'returned', 'return_requested')
GROUP BY COALESCE(t.name, c.name)
ORDER BY revenue_2024 DESC
```
(백그라운드 알림으로 받은 결과에서는 `>=`, `<`가 `&gt;=`, `&lt;`로 HTML 이스케이프되어 있었음. 위 SQL은 이를 원래 연산자로 되돌린 것임)
- 가정:
  - 대분류는 상품 카테고리의 부모(`parent_id`)로 봄. 부모가 없으면 해당 카테고리 자신을 대분류로 씀
  - 매출은 `SUM(order_items.subtotal)`(라인 할인 반영)임
  - 기간은 `ordered_at` 기준 2024년이며, 취소·반품·반품 요청 상태는 제외함
  - 매출이 없는 카테고리는 결과에 나오지 않음

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
ORDER BY mpp.avg_rating DESC NULLS LAST, mpp.review_count DESC, mpp.name
LIMIT 5;
```
- 가정: `mv_product_performance`에 이미 있는 `review_count`와 `avg_rating`을 그대로 씀. 평균 별점이 같으면 리뷰 수가 많은 순, 그다음 상품명 순으로 정렬함. 상품명만 출력함

## N9. 현재 재고가 0인 판매 중 상품은 몇 개야?
| product_count |
|---|
| 1 |

```sql
SELECT COUNT(*) AS product_count
FROM ecommerce_ko.public.products AS p
WHERE p.is_active = TRUE
  AND p.stock_qty = 0
```
- 가정: "판매 중"은 `is_active = TRUE`로 해석함. `is_active`가 판매 상태를 이미 반영한다고 보고 `discontinued_at`은 쓰지 않음. 재고 0은 `stock_qty = 0`과 정확히 일치하는 조건으로 판별함

## N10. 2024년에 발송된 배송 건의 택배사별 평균 배송 소요일은?
| carrier | avg_delivery_days |
|---|---|
| 로젠택배 | 2.5270394134 |
| 한진택배 | 2.523255814 |
| 우체국택배 | 2.4787735849 |
| CJ대한통운 | 2.5160241523 |

```sql
SELECT s.carrier, CAST(AVG(EXTRACT(EPOCH FROM (s.delivered_at - s.shipped_at)) / 86400.0) AS NUMERIC) AS avg_delivery_days
FROM ecommerce_ko.public.shipping AS s
WHERE s.shipped_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND s.shipped_at < TIMESTAMP '2025-01-01 00:00:00'
GROUP BY s.carrier
ORDER BY s.carrier
```
- 가정: 소요일은 `delivered_at - shipped_at`을 일 단위(소수 포함)로 환산한 값임. 기간은 `shipped_at` 기준 2024년임. `delivered_at`이 NULL인 미배송 건은 AVG 계산에서 자동으로 빠짐. 결과는 택배사명 순으로 정렬함
