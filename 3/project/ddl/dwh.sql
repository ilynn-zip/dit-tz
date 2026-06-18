-- Схема DWH
CREATE SCHEMA IF NOT EXISTS dwh;

-- Измерение клиентов
CREATE TABLE IF NOT EXISTS dwh.dim_customer (
    customer_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(255),
    email VARCHAR(255),
    city VARCHAR(255),
    created_at TIMESTAMP
);

-- Измерение товаров
CREATE TABLE IF NOT EXISTS dwh.dim_product (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(100),
    price NUMERIC(10,2),
    currency VARCHAR(10),
    is_active BOOLEAN
);

-- Измерение даты
CREATE TABLE IF NOT EXISTS dwh.dim_date (
    date_id DATE PRIMARY KEY,
    year INT,
    quarter INT,
    month INT,
    day INT,
    day_of_week INT,
    day_name VARCHAR(20),
    month_name VARCHAR(20)
);

-- Факт заказов
CREATE TABLE IF NOT EXISTS dwh.fact_order (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES dwh.dim_customer(customer_id),
    product_id VARCHAR(50) NOT NULL REFERENCES dwh.dim_product(product_id),
    date_id DATE NOT NULL REFERENCES dwh.dim_date(date_id),
    quantity INT,
    unit_price NUMERIC(10,2),
    total_amount NUMERIC(10,2),
    status VARCHAR(50)
);

-- Факт платежей
CREATE TABLE IF NOT EXISTS dwh.fact_payment (
    payment_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50),
    customer_id VARCHAR(50) NOT NULL REFERENCES dwh.dim_customer(customer_id),
    date_id DATE NOT NULL REFERENCES dwh.dim_date(date_id),
    amount NUMERIC(10,2),
    currency VARCHAR(10),
    payment_method VARCHAR(50)
);

-- Факт событий
CREATE TABLE IF NOT EXISTS dwh.fact_event (
    event_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES dwh.dim_customer(customer_id),
    product_id VARCHAR(50) REFERENCES dwh.dim_product(product_id),
    date_id DATE NOT NULL REFERENCES dwh.dim_date(date_id),
    event_type VARCHAR(50)
);

-- Таблица для хранения времени последней загрузки
CREATE TABLE IF NOT EXISTS dwh.etl_control (
    table_name VARCHAR(50) PRIMARY KEY,
    last_load_date TIMESTAMP NOT NULL DEFAULT '1900-01-01'
);

-- Инициализация
INSERT INTO dwh.etl_control (table_name, last_load_date)
VALUES 
    ('fact_order', '1900-01-01'),
    ('fact_payment', '1900-01-01'),
    ('fact_event', '1900-01-01'),
    ('dim_customer', '1900-01-01'),
    ('dim_product', '1900-01-01')
ON CONFLICT (table_name) DO NOTHING;