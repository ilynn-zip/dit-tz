import pandas as pd
import logging
from sqlalchemy import text
from datetime import datetime
from src.utils.db_conn import get_engine

logging.basicConfig(level=logging.INFO)

class DWHLoader:
    def __init__(self):
        self.engine = get_engine()

    def get_last_load(self, table_name):
        """
        время последней загрузки для таблицы
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT last_load_date FROM dwh.etl_control WHERE table_name = :table_name"),
                {"table_name": table_name}
            ).scalar()
            return result if result else datetime(1900, 1, 1)

    def update_last_load(self, table_name, new_date):
        """
        обновление времени последней загрузки
        """
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE dwh.etl_control 
                    SET last_load_date = :new_date 
                    WHERE table_name = :table_name
                """),
                {"new_date": new_date, "table_name": table_name}
            )

    def create_unknown_members(self):
        """
        создаёт записи-заглушки в измерениях
        если их ещё нет
        """
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dwh.dim_customer (customer_id, full_name, email, city, created_at)
                VALUES ('UNKNOWN', 'Unknown Customer', NULL, NULL, NULL)
                ON CONFLICT (customer_id) DO NOTHING
            """))
            conn.execute(text("""
                INSERT INTO dwh.dim_product (product_id, product_name, category, price, currency, is_active)
                VALUES ('UNKNOWN', 'Unknown Product', NULL, NULL, NULL, NULL)
                ON CONFLICT (product_id) DO NOTHING
            """))

    def load_dim_customer(self):
        """
        загрузка клиентов
        только новые customer_id
        """
        last_load = self.get_last_load('dim_customer')
        with self.engine.begin() as conn:
            query = """
                INSERT INTO dwh.dim_customer (customer_id, full_name, email, city, created_at)
                SELECT s.customer_id, s.full_name, s.email, s.city, s.created_at
                FROM staging.stg_customers s
                LEFT JOIN dwh.dim_customer d ON s.customer_id = d.customer_id
                WHERE d.customer_id IS NULL
                  AND s.created_at > :last_load
            """
            result = conn.execute(text(query), {"last_load": last_load})
            inserted = result.rowcount
            
            if inserted > 0:
                new_last_load = conn.execute(
                    text("SELECT MAX(created_at) FROM staging.stg_customers WHERE created_at > :last_load"),
                    {"last_load": last_load}
                ).scalar()
                if new_last_load:
                    self.update_last_load('dim_customer', new_last_load)
            logging.info(f"Загружено {inserted} новых клиентов в dwh.dim_customer")

    def load_dim_product(self):
        """
        загрузка товаров
        только новые product_id
        """
        last_load = self.get_last_load('dim_product')
        with self.engine.begin() as conn:
            query = """
                INSERT INTO dwh.dim_product (product_id, product_name, category, price, currency, is_active)
                SELECT s.product_id, s.product_name, s.category, s.price, s.currency, s.is_active
                FROM staging.stg_products s
                LEFT JOIN dwh.dim_product d ON s.product_id = d.product_id
                WHERE d.product_id IS NULL
            """
            result = conn.execute(text(query))
            inserted = result.rowcount
            if inserted > 0:
                self.update_last_load('dim_product', datetime.now())
            logging.info(f"Загружено {inserted} новых товаров в dwh.dim_product")

    def load_dim_date(self):
        """
        генерация измерений даты
        только новые даты
        """
        with self.engine.connect() as conn:
            query = """
                SELECT DISTINCT order_timestamp::DATE AS dt FROM staging.stg_orders WHERE order_timestamp IS NOT NULL
                UNION
                SELECT DISTINCT payment_timestamp::DATE FROM staging.stg_payments WHERE payment_timestamp IS NOT NULL
                UNION
                SELECT DISTINCT event_timestamp::DATE FROM staging.stg_events WHERE event_timestamp IS NOT NULL
            """
            df_dates = pd.read_sql(query, conn)
            if df_dates.empty:
                logging.warning("Нет данных для генерации dim_date")
                return
            
            df_dates['dt'] = pd.to_datetime(df_dates['dt'])
            
            existing_dates = pd.read_sql("SELECT date_id FROM dwh.dim_date", conn)['date_id']

            new_dates = df_dates[~df_dates['dt'].isin(existing_dates)]
            if new_dates.empty:
                logging.info("Нет новых дат для добавления в dwh.dim_date")
                return
            
            new_dates['date_id'] = new_dates['dt']
            new_dates['year'] = new_dates['dt'].dt.year
            new_dates['quarter'] = new_dates['dt'].dt.quarter
            new_dates['month'] = new_dates['dt'].dt.month
            new_dates['day'] = new_dates['dt'].dt.day
            new_dates['day_of_week'] = new_dates['dt'].dt.isocalendar().day
            new_dates['day_name'] = new_dates['dt'].dt.day_name()
            new_dates['month_name'] = new_dates['dt'].dt.month_name()

            new_dates = new_dates.drop(columns=['dt'])
            
            with self.engine.begin() as conn2:
                new_dates.to_sql('dim_date', conn2, schema='dwh', if_exists='append', index=False)
            logging.info(f"Добавлено {len(new_dates)} новых дат в dwh.dim_date")

    def load_fact_order(self):
        """
        загрузка заказов
        только новые order_timestamp
        """
        last_load = self.get_last_load('fact_order')
        with self.engine.begin() as conn:
            query = """
                INSERT INTO dwh.fact_order (order_id, customer_id, product_id, date_id, quantity, unit_price, total_amount, status)
                SELECT 
                    o.order_id,
                    COALESCE(c.customer_id, 'UNKNOWN') AS customer_id,
                    COALESCE(p.product_id, 'UNKNOWN') AS product_id,
                    o.order_timestamp::DATE AS date_id,
                    o.quantity,
                    o.unit_price,
                    o.quantity * o.unit_price AS total_amount,
                    o.status
                FROM staging.stg_orders o
                LEFT JOIN dwh.dim_customer c ON o.customer_id = c.customer_id
                LEFT JOIN dwh.dim_product p ON o.product_id = p.product_id
                WHERE o.order_timestamp > :last_load
                ON CONFLICT (order_id) DO NOTHING
            """
            result = conn.execute(text(query), {"last_load": last_load})
            inserted = result.rowcount
            
            if inserted > 0:
                new_last_load = conn.execute(
                    text("SELECT MAX(order_timestamp) FROM staging.stg_orders WHERE order_timestamp > :last_load"),
                    {"last_load": last_load}
                ).scalar()
                if new_last_load:
                    self.update_last_load('fact_order', new_last_load)
            logging.info(f"Загружено {inserted} новых заказов в dwh.fact_order")

    def load_fact_payment(self):
        """
        загрузка платежей
        только новые payment_timestamp
        """
        last_load = self.get_last_load('fact_payment')
        with self.engine.begin() as conn:
            query = """
                INSERT INTO dwh.fact_payment (payment_id, order_id, customer_id, date_id, amount, currency, payment_method)
                SELECT 
                    p.payment_id,
                    p.order_id,
                    COALESCE(c.customer_id, 'UNKNOWN') AS customer_id,
                    p.payment_timestamp::DATE AS date_id,
                    p.amount,
                    p.currency,
                    p.payment_method
                FROM staging.stg_payments p
                LEFT JOIN staging.stg_orders o ON p.order_id = o.order_id
                LEFT JOIN dwh.dim_customer c ON o.customer_id = c.customer_id
                WHERE p.payment_timestamp > :last_load
                ON CONFLICT (payment_id) DO NOTHING
            """
            result = conn.execute(text(query), {"last_load": last_load})
            inserted = result.rowcount
            
            if inserted > 0:
                new_last_load = conn.execute(
                    text("SELECT MAX(payment_timestamp) FROM staging.stg_payments WHERE payment_timestamp > :last_load"),
                    {"last_load": last_load}
                ).scalar()
                if new_last_load:
                    self.update_last_load('fact_payment', new_last_load)
            logging.info(f"Загружено {inserted} новых платежей в dwh.fact_payment")

    def load_fact_event(self):
        """
        загрузка событий
        только новые event_timestamp
        """
        last_load = self.get_last_load('fact_event')
        with self.engine.begin() as conn:
            query = """
                INSERT INTO dwh.fact_event (event_id, customer_id, product_id, date_id, event_type)
                SELECT 
                    e.event_id,
                    COALESCE(c.customer_id, 'UNKNOWN') AS customer_id,
                    COALESCE(p.product_id, 'UNKNOWN') AS product_id,
                    e.event_timestamp::DATE AS date_id,
                    e.event_type
                FROM staging.stg_events e
                LEFT JOIN dwh.dim_customer c ON e.customer_id = c.customer_id
                LEFT JOIN dwh.dim_product p ON e.product_id = p.product_id
                WHERE e.event_timestamp > :last_load
                ON CONFLICT (event_id) DO NOTHING
            """
            result = conn.execute(text(query), {"last_load": last_load})
            inserted = result.rowcount
            
            if inserted > 0:
                new_last_load = conn.execute(
                    text("SELECT MAX(event_timestamp) FROM staging.stg_events WHERE event_timestamp > :last_load"),
                    {"last_load": last_load}
                ).scalar()
                if new_last_load:
                    self.update_last_load('fact_event', new_last_load)
            logging.info(f"Загружено {inserted} новых событий в dwh.fact_event")

    def load_all(self):
        """
        запускает загрузку DWH
        """
        logging.info("\033[94mНачало инкрементальной загрузки DWH\033[0m")
        
        # создание заглушки
        self.create_unknown_members()
        
        # загрузка измерений
        self.load_dim_customer()
        self.load_dim_product()
        self.load_dim_date()
        
        # загрузка фактов
        self.load_fact_order()
        self.load_fact_payment()
        self.load_fact_event()
        
        logging.info("\033[92mИнкрементальная загрузка DWH завершена\033[0m")