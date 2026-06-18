-- 1. Топ-10 клиентов по сумме покупок
select
	c.customer_id
    ,c.full_name
    ,sum(f.total_amount) as total_spent
from
	dwh.fact_order f
join dwh.dim_customer c on
	f.customer_id = c.customer_id
group by
	c.customer_id
	,c.full_name
order by
	total_spent desc
limit 10;


-- 2. Выручка по месяцам (за всё время)
select
	d.year
	,d.month
	,d.month_name
	,sum(f.total_amount) as revenue
from
	dwh.fact_order f
join dwh.dim_date d on
	f.date_id = d.date_id
group by
	d.year
	,d.month
	,d.month_name
order by
	d.year
	,d.month;


-- 3. Самые популярные товары (по количеству проданных единиц)
select
	p.product_id
	,p.product_name
	,p.category
	,sum(f.quantity) as total_quantity_sold
	,count(distinct f.order_id) as number_of_orders
from
	dwh.fact_order f
join dwh.dim_product p on
	f.product_id = p.product_id
group by
	p.product_id
	,p.product_name
	,p.category
order by
	total_quantity_sold desc
limit 10;


-- 4. Последняя активность (дата) топ-5 пользователей по сумме покупок
with top_customers as (
select
	customer_id
	,sum(total_amount) as spent
from
	dwh.fact_order
group by
	customer_id
order by
	spent desc
limit 5
)
select
	tc.customer_id
	,max(e.date_id) as last_activity_date
from
	top_customers tc
left join dwh.fact_event e on
	tc.customer_id = e.customer_id
group by
	tc.customer_id
	,tc.spent
order by
	tc.spent desc;


-- 5. Пользователи без заказов
select
	c.customer_id
	,c.full_name
	,c.email
	,c.created_at
from
	dwh.dim_customer c
left join dwh.fact_order f on
	c.customer_id = f.customer_id
where
	f.order_id is null
	and c.customer_id != 'UNKNOWN'
	-- исключаем заглушку
order by
	c.customer_id;
