# J22 한국어 DB 시험 4: ecommerce_ko 10문항 재시험 (매출 SQL 속성 추가, 집계 뷰 설명 보강)

- 일시: 2026-11-08 / 실행: Claude Code (Opus 5.5) / 읽기 전용
- 조건: 매출 SQL 속성을 추가하고 집계 뷰 설명을 보강한 뒤 실행함. 변경은 t2-claude가 했으며, 여기 적은 내용은 브리프를 옮긴 것임
- 사용 도구: `ask_question`만 사용. U1부터 N10까지 순서대로 1회씩 호출했고, 이전 호출이 끝난 뒤에 다음 호출을 보냄
- DB 지정: `ask_question`에 database 인자가 없어서 지정하지 않음. 생성된 SQL은 모두 `ecommerce_ko.public.*`를 참조함
- 정답 판정을 하지 않았고, 이전 결과와도 비교하지 않음 (브리프 지시)
- wall-clock은 호출 앞뒤 타임스탬프의 차이이며, 수백 ms 정도의 오버헤드가 포함됨

## 요약
| # | 질문 | wall-clock | 오류 | 행 수 |
|---|---|---|---|---|
| U1 | 2024년 월별 매출액 | 32.8초 | 없음 | 12 |
| U2 | 2024년 매출 상위 5개 상품 | 30.6초 | 없음 | 5 |
| U3 | 2024년 서울 지역 매출 | 26.6초 | 없음 | 1 |
| N4 | 2024년 반품 사유별 건수 | 20.3초 | 없음 | 6 |
| N5 | 등급별 고객 수와 1인당 평균 매출 | 45.1초 | 없음 | 4 |
| N6 | 2024년 결제 수단별 결제 완료 금액 | 26.5초 | 없음 | 6 |
| N7 | 대분류 카테고리별 2024년 매출 | 98.5초 | 없음 | 18 |
| N8 | 리뷰 10건 이상, 평균 별점 상위 5개 | 36.8초 | 없음 | 5 |
| N9 | 재고 0인 판매 중 상품 수 | 62.1초 | 없음 | 1 |
| N10 | 2024년 택배사별 평균 배송 소요일 | 31.6초 | 없음 | 4 |

---

## U1. 2024년 월별 매출액은?
| month | revenue |
|---|---|
| 2024-01-01 | 288908320 |
| 2024-02-01 | 403127749 |
| 2024-03-01 | 519844502 |
| 2024-04-01 | 451877581 |
| 2024-05-01 | 425264478 |
| 2024-06-01 | 362715211 |
| 2024-07-01 | 343929897 |
| 2024-08-01 | 404803340 |
| 2024-09-01 | 536079841 |
| 2024-10-01 | 417430467 |
| 2024-11-01 | 543313372 |
| 2024-12-01 | 417148762 |

```sql
SELECT DATE_TRUNC('month', o.ordered_at) AS month, SUM(o.total_amount) AS revenue
FROM ecommerce_ko.public.orders AS o
WHERE o.status NOT IN ('cancelled', 'returned', 'return_requested')
  AND o.ordered_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND o.ordered_at < TIMESTAMP '2025-01-01 00:00:00'
GROUP BY DATE_TRUNC('month', o.ordered_at)
ORDER BY month;
```
- 가정:
  - 공식 매출 정의를 따름: `orders.total_amount`의 합계이며, 취소·반품·반품 요청 주문은 제외하고, 기간은 `ordered_at` 기준임
  - agent는 "월별 매출 뷰에는 반품이 포함된다"는 설명을 보고 그 뷰를 쓰지 않았음
  - 월 시리즈를 따로 생성하지 않으므로, 해당 주문이 없는 달은 결과에서 빠짐

## U2. 2024년 매출 상위 5개 상품은?
| 순위 | name | product_revenue |
|---|---|---|
| 1 | Razer Blade 18 블랙 | 164281800 |
| 2 | Razer Blade 16 실버 | 135517100 |
| 3 | MacBook Air 15 M3 실버 | 124458800 |
| 4 | ASUS Dual RTX 4060 Ti 블랙 | 105999300 |
| 5 | ASUS Dual RTX 5070 Ti 실버 | 103694900 |

```sql
SELECT p.name, SUM(oi.subtotal) AS product_revenue
FROM ecommerce_ko.public.order_items AS oi
JOIN ecommerce_ko.public.orders AS o ON o.id = oi.order_id
JOIN ecommerce_ko.public.products AS p ON p.id = oi.product_id
WHERE CAST(o.status AS TEXT) NOT IN ('cancelled', 'returned', 'return_requested')
  AND o.ordered_at >= '2024-01-01'
  AND o.ordered_at < '2025-01-01'
GROUP BY p.id, p.name
ORDER BY product_revenue DESC, p.id
LIMIT 5;
```
- 가정:
  - 상품 매출 정의를 따름: `order_items.subtotal`의 합계이며, 취소·반품·반품 요청 주문은 제외함
  - 기간은 `ordered_at` 기준 2024년임
  - 속성 가이드에 따라 상품명과 매출액을 함께 출력함. 동점이면 상품 id 순으로 정렬함
  - enum 비교가 실패할 경우에 대비해 status를 TEXT로 캐스팅함

## U3. 2024년 서울 지역 매출은?
| revenue |
|---|
| 367763602 |

```sql
SELECT SUM(v.total_amount) AS revenue
FROM ecommerce_ko.public.v_order_detail AS v
WHERE v.order_status NOT IN ('cancelled', 'returned', 'return_requested')
  AND v.delivery_address LIKE '서울%'
  AND v.ordered_at >= '2024-01-01'
  AND v.ordered_at < '2025-01-01'
```
- 가정:
  - 공식 매출 정의(취소·반품·반품 요청 제외, 기간은 `ordered_at` 기준)를 적용함
  - 지역 필터에 배송지 주소가 필요해서, 주문 상태·금액·주문 일시·배송지를 모두 가진 `v_order_detail`을 사용함
  - 서울은 `delivery_address`가 '서울'로 시작하는 주소로 판별함
  - 일치하는 행이 없으면 NULL이 반환되며, 0으로 바꾸지 않음

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
WHERE r.requested_at >= '2024-01-01' AND r.requested_at < '2025-01-01'
GROUP BY r.reason
ORDER BY return_count DESC, r.reason;
```
- 가정:
  - "접수"를 `requested_at`(반품 요청일시, 즉 반품 접수일)으로 매핑함
  - 검증된 경로에는 `created_at`도 선택지로 있었지만, "접수된"에는 `requested_at`이 더 잘 맞는다고 판단함
  - 건수가 0인 사유는 결과에 나오지 않음. 동점이면 사유명 순으로 정렬함

## N5. 고객 등급별 고객 수와, 2024년에 구매한 고객 기준 1인당 평균 매출은? 취소·반품(반품 요청 포함) 주문은 제외해.
| grade | customer_count | avg_revenue_per_buyer_2024 |
|---|---|---|
| BRONZE | 3859 | 1616041.9446022727 |
| SILVER | 479 | 2471140.446366782 |
| GOLD | 524 | 3232188.1639784947 |
| VIP | 368 | 6777027.6480263155 |

```sql
WITH grade_counts AS (
  SELECT c.grade AS grade, COUNT(*) AS customer_count
  FROM ecommerce_ko.public.customers AS c
  GROUP BY c.grade
),
buyer_revenue AS (
  SELECT c.grade AS grade,
         SUM(o.total_amount) AS revenue,
         COUNT(DISTINCT o.customer_id) AS buyer_count
  FROM ecommerce_ko.public.orders AS o
  INNER JOIN ecommerce_ko.public.customers AS c ON o.customer_id = c.id
  WHERE o.ordered_at >= '2024-01-01'
    AND o.ordered_at < '2025-01-01'
    AND o.status NOT IN ('cancelled', 'returned', 'return_requested')
  GROUP BY c.grade
)
SELECT g.grade,
       g.customer_count,
       CAST(b.revenue AS NUMERIC) / NULLIF(b.buyer_count, 0) AS avg_revenue_per_buyer_2024
FROM grade_counts AS g
LEFT JOIN buyer_revenue AS b ON g.grade = b.grade
ORDER BY g.grade;
```
- 가정:
  - 고객 수는 `customers` 전체를 등급별로 센 값임
  - 평균 매출은 유효 주문의 `total_amount` 합계를 2024년 고유 구매 고객 수로 나눈 값임. 취소·반품·반품 요청 주문은 공식 매출 정의대로 제외함
  - 2024년 구매 고객이 없는 등급도 행은 유지하고 평균만 NULL로 둠(LEFT JOIN, NULLIF)
  - 기간은 `ordered_at` 기준이며, 정렬은 등급 enum 순서를 따름

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
  - 2024년은 `paid_at`(결제 완료 일시) 기준임
  - `v_payment_summary`는 연도로 거를 수 없어서 쓰지 않음
  - Revenue 속성은 orders에 정의되어 있어서 이번에는 사용하지 않음
  - 완료된 결제가 없는 결제 수단은 결과에 나오지 않음

## N7. 대분류 카테고리별 2024년 매출은? 취소·반품(반품 요청 포함) 주문은 제외해.
| top_category_name | revenue_2024 |
|---|---|
| 노트북 | 1383992100 |
| 그래픽카드 | 787204800 |
| 모니터 | 719200400 |
| CPU | 509234900 |
| 메인보드 | 395151200 |
| 스피커/헤드셋 | 229793600 |
| 저장장치 | 204264200 |
| 메모리(RAM) | 198989500 |
| 키보드 | 197761300 |
| 파워서플라이(PSU) | 191064500 |
| 마우스 | 177811800 |
| 케이스 | 139545800 |
| 네트워크 장비 | 135795600 |
| 데스크톱 PC | 123881700 |
| 쿨링 | 96034300 |
| 소프트웨어 | 52085100 |
| 프린터/스캐너 | 42745700 |
| UPS/전원 | 28697000 |

```sql
SELECT
  CASE c.depth WHEN 0 THEN c.name WHEN 1 THEN c1.name ELSE c2.name END AS top_category_name,
  SUM(oi.subtotal) AS revenue_2024
FROM ecommerce_ko.public.order_items AS oi
INNER JOIN ecommerce_ko.public.orders AS o ON oi.order_id = o.id
INNER JOIN ecommerce_ko.public.mv_product_performance AS p ON oi.product_id = p.product_id
INNER JOIN ecommerce_ko.public.categories AS c ON c.name = p.category
LEFT JOIN ecommerce_ko.public.categories AS c1 ON c1.id = c.parent_id
LEFT JOIN ecommerce_ko.public.categories AS c2 ON c2.id = c1.parent_id
WHERE o.status NOT IN ('cancelled', 'returned', 'return_requested')
  AND o.ordered_at >= '2024-01-01'
  AND o.ordered_at < '2025-01-01'
GROUP BY CASE c.depth WHEN 0 THEN c.name WHEN 1 THEN c1.name ELSE c2.name END
ORDER BY revenue_2024 DESC, top_category_name
```
- 가정:
  - products 테이블이 사용 가능 목록에 없어서, 상품과 카테고리를 `mv_product_performance`로 연결함. 이 뷰의 `category`(이름 문자열)를 `categories.name`에 매핑함
  - 카테고리 이름은 고유하다고 가정함
  - `parent_id`를 따라 depth=0(대분류)까지 올라감
  - 매출은 정의대로 `order_items.subtotal`의 합계이며, 취소·반품·반품 요청 주문은 제외하고, 기간은 `ordered_at` 기준 2024년임
  - 매출이 없는 대분류는 INNER JOIN 때문에 결과에서 빠짐
  - 검증 단계에서 agent 스스로 "이름으로 조인하는 경로는 그럴듯하지만 불완전하다(plausible, if imperfect)"고 언급함

## N8. 리뷰가 10건 이상인 상품 중 평균 별점 상위 5개는?
| 순위 | name |
|---|---|
| 1 | LG 32UN880 에르고 화이트 |
| 2 | WD Elements 2TB 블랙 |
| 3 | Windows 11 Home 블랙 |
| 4 | Dell XPS Desktop 8960 실버 |
| 5 | Arctic Liquid Freezer III Pro 420 A-RGB 실버 |

(평균 별점과 리뷰 수 컬럼은 출력하지 않고 상품명만 반환함)

```sql
SELECT p.name
FROM ecommerce_ko.public.products AS p
INNER JOIN ecommerce_ko.public.reviews AS r ON r.product_id = p.id
GROUP BY p.id, p.name
HAVING COUNT(r.id) >= 10
ORDER BY AVG(r.rating) DESC, COUNT(r.id) DESC, p.name
LIMIT 5;
```
- 가정:
  - 원천 데이터로 계산하려고 `reviews`를 `products`와 조인해 상품별로 직접 집계함. 리뷰 10건 이상은 HAVING으로 거름
  - 평균 별점이 같으면 리뷰 수가 많은 순, 그다음 상품명 순으로 정렬함
  - 상품명만 출력함. 상품명이 고유하지 않을 수 있어서 id와 name으로 함께 그룹화함

## N9. 현재 재고가 0인 판매 중 상품은 몇 개야?
| product_count |
|---|
| 1 |

```sql
SELECT COUNT(*) AS product_count
FROM ecommerce_ko.public.products AS p
WHERE p.stock_qty = 0
  AND p.is_active = TRUE
```
- 가정: "판매 중"은 `is_active = TRUE`로 해석함. 설명에 `is_active`가 판매 여부 플래그라고 되어 있어서 `discontinued_at IS NULL` 조건은 추가하지 않음

## N10. 2024년에 발송된 배송 건의 택배사별 평균 배송 소요일은?
| carrier | avg_delivery_days |
|---|---|
| 로젠택배 | 2.53 |
| 한진택배 | 2.52 |
| 우체국택배 | 2.48 |
| CJ대한통운 | 2.52 |

```sql
SELECT s.carrier,
       CAST(AVG(EXTRACT(EPOCH FROM (s.delivered_at - s.shipped_at)) / 86400.0) AS NUMERIC(10,2)) AS avg_delivery_days
FROM ecommerce_ko.public.shipping AS s
WHERE s.shipped_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND s.shipped_at < TIMESTAMP '2025-01-01 00:00:00'
GROUP BY s.carrier
ORDER BY s.carrier;
```
- 가정: 소요일은 `delivered_at - shipped_at`을 일 단위(소수)로 환산한 값이며, NUMERIC(10,2)로 캐스팅함. 기간은 `shipped_at` 기준 2024년임. `delivered_at`이 NULL인 미배송 건은 AVG 계산에서 자동으로 빠짐. 결과는 택배사명 순으로 정렬함
