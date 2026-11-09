"""J22-06.6: 매출 SqlAttribute 2개 생성·certify + 집계 뷰 설명 보강 (auto-ontology 컨테이너에서 실행)."""
from sqlalchemy import text
from auto_ontology.dal.session import get_engine
from auto_ontology.server.sql_attributes.service import create_sql_attribute

EXCL = "('cancelled', 'returned', 'return_requested')"
ATTRS = [
    {
        "term_id": "9c2c50d6-c5cb-4d51-a547-c1744f53c1df",  # Order (ecommerce_ko.public.orders)
        "name": "매출 (Revenue)",
        "description": (
            "매출(매출액, 판매액, 순매출). 공식 매출 정의. 주문 최종 결제 금액 orders.total_amount의 합계. "
            "취소(cancelled)·반품(returned)·반품 요청(return_requested) 주문은 제외한다. 기간은 주문 일시 orders.ordered_at 기준. "
            "월별·지역별·고객별 매출도 이 정의를 쓴다. mv_monthly_sales.revenue는 반품을 포함하므로 매출로 쓰지 않는다."
        ),
        "expression": f"SELECT SUM(o.total_amount) AS revenue FROM public.orders AS o WHERE o.status NOT IN {EXCL}",
    },
    {
        "term_id": "94ebd5e7-497d-466b-9980-33b28bf8925f",  # Order Item
        "name": "상품 매출 (Product Revenue)",
        "description": (
            "상품 매출(상품별 매출, 품목 매출). 상품별·카테고리별 매출의 공식 정의. 주문 상세 order_items.subtotal의 합계. "
            "주문(orders) 상태가 취소·반품·반품 요청인 건은 제외하고, 기간은 orders.ordered_at 기준. 상품은 products.id 단위로 묶는다(같은 이름의 다른 SKU가 있음). "
            "답할 때는 상품명과 매출액을 함께 보여 준다. mv_product_performance.total_revenue는 반품을 포함하므로 쓰지 않는다."
        ),
        "expression": (
            "SELECT oi.product_id, SUM(oi.subtotal) AS product_revenue FROM public.order_items AS oi "
            f"JOIN public.orders AS o ON o.id = oi.order_id WHERE o.status NOT IN {EXCL} GROUP BY oi.product_id"
        ),
    },
]
for a in ATTRS:
    row = create_sql_attribute(source="manual", connector="ecommerce_ko", **a)
    print("created", row.get("id"), row.get("name"))

NOTE = {
    "Monthly Sales Summary": " 주의: 이 집계 뷰(mv_monthly_sales)는 취소(cancelled)만 제외하고 반품·반품 요청을 포함한다. 공식 매출(Revenue)과 다르므로 매출 질문에는 orders에서 직접 계산한다.",
    "Product Performance": " 주의: 이 집계 뷰(mv_product_performance)의 avg_rating은 소수 첫째 자리로 반올림돼 있어 순위 비교에 부적합하다(동점 발생). 평균 별점 순위는 reviews.rating 평균으로 직접 계산한다. total_revenue는 반품을 포함한다.",
}
with get_engine().begin() as c:
    c.execute(text("update sql_attribute set certified = true where name in ('매출 (Revenue)', '상품 매출 (Product Revenue)')"))
    for name, note in NOTE.items():
        c.execute(text("update term set description = description || :n where name = :t and position('주의:' in description) = 0"), {"n": note, "t": name})
    rows = c.execute(text("select name, certified from sql_attribute order by name")).fetchall()
print(rows)
