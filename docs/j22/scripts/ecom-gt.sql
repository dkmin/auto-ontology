\pset footer off
\echo == U1 variants (2024 total): excl cancel/return | all statuses | confirmed+delivered only
select sum(total_amount) filter (where status not in ('cancelled','returned','return_requested')) excl,
       sum(total_amount) all_st,
       sum(total_amount) filter (where status in ('confirmed','delivered')) conf
from orders where ordered_at>='2024-01-01' and ordered_at<'2025-01-01';
\echo == U3 seoul variants
select count(*) filter (where o.status not in ('cancelled','returned','return_requested')) n_excl, sum(o.total_amount) filter (where o.status not in ('cancelled','returned','return_requested')) excl, count(*) n_all, sum(o.total_amount) all_st
from orders o join customer_addresses a on a.id=o.address_id where a.address1 like '서울%' and o.ordered_at>='2024-01-01' and o.ordered_at<'2025-01-01';
\echo == U2 top5 qty (excl)
select p.id,p.name,sum(oi.quantity) qty,sum(oi.subtotal) amt from order_items oi join orders o on o.id=oi.order_id join products p on p.id=oi.product_id where o.ordered_at>='2024-01-01' and o.ordered_at<'2025-01-01' and o.status not in ('cancelled','returned','return_requested') group by 1,2 order by 3 desc, 4 desc limit 6;
\echo == U2 top5 amt all statuses
select p.id,p.name,sum(oi.subtotal) amt from order_items oi join orders o on o.id=oi.order_id join products p on p.id=oi.product_id where o.ordered_at>='2024-01-01' and o.ordered_at<'2025-01-01' group by 1,2 order by 3 desc limit 5;
\echo == N4 return reasons 2024
select reason, count(*) from returns where requested_at>='2024-01-01' and requested_at<'2025-01-01' group by 1 order by 2 desc;
\echo == N5 grade: customers, 2024 avg revenue per customer (all customers in grade) and per buying customer
with r as (select customer_id, sum(total_amount) amt from orders where ordered_at>='2024-01-01' and ordered_at<'2025-01-01' and status not in ('cancelled','returned','return_requested') group by 1)
select c.grade, count(*) n_cust, count(r.customer_id) n_buyers, round(sum(coalesce(r.amt,0))/count(*),0) avg_all, round(avg(r.amt),0) avg_buyers
from customers c left join r on r.customer_id=c.id group by 1 order by 1;
\echo == N6 payment method 2024 completed
select method, count(*), sum(amount) from payments where status='completed' and paid_at>='2024-01-01' and paid_at<'2025-01-01' group by 1 order by 3 desc;
\echo == N7 top-level category revenue 2024 (excl)
with recursive t as (select id, id root from categories where parent_id is null union all select c.id, t.root from categories c join t on c.parent_id=t.id)
select rc.name, sum(oi.subtotal) amt from order_items oi join orders o on o.id=oi.order_id join products p on p.id=oi.product_id join t on t.id=p.category_id join categories rc on rc.id=t.root
where o.ordered_at>='2024-01-01' and o.ordered_at<'2025-01-01' and o.status not in ('cancelled','returned','return_requested') group by 1 order by 2 desc;
\echo == N8 top avg rating, >=10 reviews
select p.id,p.name,count(*) n, round(avg(r.rating),3) avg from reviews r join products p on p.id=r.product_id group by 1,2 having count(*)>=10 order by 4 desc, 3 desc limit 7;
\echo == N9 active products stock 0: products.stock_qty vs ledger sum
select count(*) filter (where stock_qty=0) by_col from products where is_active;
select count(*) by_ledger from (select p.id, coalesce(sum(it.quantity),0) s from products p left join inventory_transactions it on it.product_id=p.id where p.is_active group by 1) x where s<=0;
\echo == N10 carrier avg delivery days 2024 (shipped_at in 2024, delivered)
select carrier, count(*), round(avg(extract(epoch from delivered_at-shipped_at)/86400)::numeric,2) days from shipping where delivered_at is not null and shipped_at>='2024-01-01' and shipped_at<'2025-01-01' group by 1 order by 3;
