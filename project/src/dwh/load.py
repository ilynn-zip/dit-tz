import pandas as pd
import logging
from sqlalchemy import text
from src.utils.db_conn import get_engine

logging.basicConfig(level=logging.INFO)

class DWHLoader:
    def __init__(self):
        self.engine = get_engine()

    def create_unknown_members(self):
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
        with self.engine.begin() as conn:
            df = pd.read_sql("SELECT customer_id, full_name, email, city, created_at FROM staging.stg_customers", conn)
            if not df.empty:
                df.to_sql('dim_customer', conn, schema='dwh', if_exists='append', index=False)
            logging.info(f"Загружено {len(df)} клиентов в dwh.dim_customer")

    def load_dim_product(self):
        with self.engine.begin() as conn:
            df = pd.read_sql("SELECT product_id, product_name, category, price, currency, is_active FROM staging.stg_products", conn)
            if not df.empty:
                df.to_sql('dim_product', conn, schema='dwh', if_exists='append', index=False)
            logging.info(f"Загружено {len(df)} товаров в dwh.dim_product")

    def load_dim_date(self):
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
            min_date = df_dates['dt'].min()
            max_date = df_dates['dt'].max()
            date_range = pd.date_range(start=min_date, end=max_date, freq='D')
            dim_date = pd.DataFrame({'date_id': date_range})
            dim_date['year'] = dim_date['date_id'].dt.year
            dim_date['quarter'] = dim_date['date_id'].dt.quarter
            dim_date['month'] = dim_date['date_id'].dt.month
            dim_date['day'] = dim_date['date_id'].dt.day
            dim_date['day_of_week'] = dim_date['date_id'].dt.isocalendar().day
            dim_date['day_name'] = dim_date['date_id'].dt.day_name()
            dim_date['month_name'] = dim_date['date_id'].dt.month_name()
            with self.engine.begin() as conn2:
                conn2.execute(text("DELETE FROM dwh.dim_date"))
                dim_date.to_sql('dim_date', conn2, schema='dwh', if_exists='append', index=False)
            logging.info(f"Загружено {len(dim_date)} записей в dwh.dim_date")

    def load_fact_order(self):
        with self.engine.begin() as conn:
            query = """
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
            """
            df = pd.read_sql(query, conn)
            if not df.empty:
                dim_dates = pd.read_sql("SELECT date_id FROM dwh.dim_date", conn)['date_id']
                min_date_in_dim = pd.read_sql("SELECT MIN(date_id) FROM dwh.dim_date", conn).iloc[0,0]
                df['date_id'] = df['date_id'].where(df['date_id'].isin(dim_dates), min_date_in_dim)
                df.to_sql('fact_order', conn, schema='dwh', if_exists='append', index=False)
            logging.info(f"Загружено {len(df)} заказов в dwh.fact_order")

    def load_fact_payment(self):
        with self.engine.begin() as conn:
            query = """
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
            """
            df = pd.read_sql(query, conn)
            if not df.empty:
                dim_dates = pd.read_sql("SELECT date_id FROM dwh.dim_date", conn)['date_id']
                min_date_in_dim = pd.read_sql("SELECT MIN(date_id) FROM dwh.dim_date", conn).iloc[0,0]
                df['date_id'] = df['date_id'].where(df['date_id'].isin(dim_dates), min_date_in_dim)
                # Заменяем NaN в order_id на None (что даст NULL в БД)
                df['order_id'] = df['order_id'].where(pd.notna(df['order_id']), None)
                df.to_sql('fact_payment', conn, schema='dwh', if_exists='append', index=False)
            logging.info(f"Загружено {len(df)} платежей в dwh.fact_payment")

    def load_fact_event(self):
        with self.engine.begin() as conn:
            query = """
                SELECT 
                    e.event_id,
                    COALESCE(c.customer_id, 'UNKNOWN') AS customer_id,
                    COALESCE(p.product_id, 'UNKNOWN') AS product_id,
                    e.event_timestamp::DATE AS date_id,
                    e.event_type
                FROM staging.stg_events e
                LEFT JOIN dwh.dim_customer c ON e.customer_id = c.customer_id
                LEFT JOIN dwh.dim_product p ON e.product_id = p.product_id
            """
            df = pd.read_sql(query, conn)
            if not df.empty:
                dim_dates = pd.read_sql("SELECT date_id FROM dwh.dim_date", conn)['date_id']
                min_date_in_dim = pd.read_sql("SELECT MIN(date_id) FROM dwh.dim_date", conn).iloc[0,0]
                df['date_id'] = df['date_id'].where(df['date_id'].isin(dim_dates), min_date_in_dim)
                df.to_sql('fact_event', conn, schema='dwh', if_exists='append', index=False)
            logging.info(f"Загружено {len(df)} событий в dwh.fact_event")

    def load_all(self):
        logging.info("Начало загрузки DWH")
        with self.engine.begin() as conn:
            # Удаляем факты
            conn.execute(text("DELETE FROM dwh.fact_payment"))
            conn.execute(text("DELETE FROM dwh.fact_event"))
            conn.execute(text("DELETE FROM dwh.fact_order"))
            # Удаляем измерения (кроме UNKNOWN)
            conn.execute(text("DELETE FROM dwh.dim_customer WHERE customer_id != 'UNKNOWN'"))
            conn.execute(text("DELETE FROM dwh.dim_product WHERE product_id != 'UNKNOWN'"))
            conn.execute(text("DELETE FROM dwh.dim_date"))
        self.create_unknown_members()
        self.load_dim_customer()
        self.load_dim_product()
        self.load_dim_date()
        self.load_fact_order()
        self.load_fact_payment()
        self.load_fact_event()
        logging.info("Загрузка DWH завершена")