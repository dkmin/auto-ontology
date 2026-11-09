# J22 한국어 DB 시험: ecommerce_ko (방식 A, auto-ontology ask_question)

- 일시: 2026-11-08 / 실행: Claude Code (Opus 5.5) / 읽기 전용
- 사용 도구: `ask_question`만 사용. Q1→Q2→Q3 순서로 1회씩 호출함
- DB 지정: `ask_question`에는 database 인자가 없어서 지정하지 않고 그대로 호출함. 생성된 SQL은 모두 `ecommerce_ko.public.*`를 참조함
- 정답 판정은 하지 않음 (브리프 지시)
- 시간은 호출 직전과 직후에 찍은 타임스탬프의 차이임

## 요약
| 질문 | 사용 DB | wall-clock | 오류 | 행 수 |
|---|---|---|---|---|
| Q1 2024 월별 매출 | ecommerce_ko | 37.2초 | 없음 | 12 |
| Q2 2024 매출 상위 5개 상품 | ecommerce_ko | 33.9초 | 없음 | 5 |
| Q3 서울 배송지 2024 주문 건수·매출 | ecommerce_ko | 31.7초 | 없음 | 1 |

## Q1. 2024년 월별 매출액을 알려줘. 매출은 주문 최종 결제 금액 기준이고 취소·반품(반품 요청 포함) 주문은 제외해.
| 월 | monthly_revenue |
|---|---|
| 2024-01 | 288908320 |
| 2024-02 | 403127749 |
| 2024-03 | 519844502 |
| 2024-04 | 451877581 |
| 2024-05 | 425264478 |
| 2024-06 | 362715211 |
| 2024-07 | 343929897 |
| 2024-08 | 404803340 |
| 2024-09 | 536079841 |
| 2024-10 | 417430467 |
| 2024-11 | 543313372 |
| 2024-12 | 417148762 |

```sql
SELECT DATE_TRUNC('month', o.ordered_at) AS order_month, SUM(o.total_amount) AS monthly_revenue
FROM ecommerce_ko.public.orders AS o
WHERE o.status NOT IN ('cancelled', 'returned', 'return_requested')
  AND o.ordered_at >= '2024-01-01'
  AND o.ordered_at < '2025-01-01'
GROUP BY DATE_TRUNC('month', o.ordered_at)
ORDER BY order_month
```
- agent가 밝힌 가정: 최종 결제 금액은 `orders.total_amount`로 봄. 월별 뷰는 취소·반품 제외 기준을 확인할 수 없어서 쓰지 않았음

## Q2. 2024년 매출 상위 5개 상품과 각 매출액은? 취소·반품(반품 요청 포함) 주문은 제외해.
| 순위 | product_name | total_revenue |
|---|---|---|
| 1 | Razer Blade 18 블랙 | 164281800 |
| 2 | Razer Blade 16 실버 | 135517100 |
| 3 | MacBook Air 15 M3 실버 | 124458800 |
| 4 | ASUS Dual RTX 4060 Ti 블랙 | 105999300 |
| 5 | ASUS Dual RTX 5070 Ti 실버 | 103694900 |

```sql
SELECT p.name AS product_name, SUM(oi.subtotal) AS total_revenue
FROM ecommerce_ko.public.order_items AS oi
INNER JOIN ecommerce_ko.public.orders AS o ON oi.order_id = o.id
INNER JOIN ecommerce_ko.public.products AS p ON oi.product_id = p.id
WHERE o.ordered_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND o.ordered_at < TIMESTAMP '2025-01-01 00:00:00'
  AND o.status NOT IN ('cancelled', 'returned', 'return_requested')
GROUP BY p.id, p.name
ORDER BY total_revenue DESC, p.name
LIMIT 5
```
- agent가 밝힌 가정: 매출은 `order_items.subtotal`(할인을 반영한 라인 소계)의 합계임. 기간은 `ordered_at` 기준이며, 사전 집계 뷰는 연도·상태로 거를 수 없어서 쓰지 않았음

## Q3. 서울 지역 배송지로 들어온 2024년 주문 건수와 매출액은? 취소·반품(반품 요청 포함) 주문은 제외해.
| order_count | total_sales |
|---|---|
| 355 | 367763602 |

```sql
SELECT COUNT(o.id) AS order_count,
       COALESCE(SUM(o.total_amount), 0) AS total_sales
FROM ecommerce_ko.public.orders AS o
INNER JOIN ecommerce_ko.public.customer_addresses AS ca ON o.address_id = ca.id
WHERE ca.address1 LIKE '서울%'
  AND o.ordered_at >= TIMESTAMP '2024-01-01 00:00:00'
  AND o.ordered_at < TIMESTAMP '2025-01-01 00:00:00'
  AND CAST(o.status AS TEXT) NOT IN ('cancelled', 'returned', 'return_requested')
```
- agent가 밝힌 가정: 서울 지역은 `customer_addresses.address1`이 '서울'로 시작하는 주소로 봄. 매출은 `SUM(orders.total_amount)`로 계산했고, 할인과 배송비는 따로 차감하지 않음
