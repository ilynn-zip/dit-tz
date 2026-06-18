-- Создаём схему staging, если её нет
CREATE SCHEMA IF NOT EXISTS staging;

-- Таблица клиентов
CREATE TABLE IF NOT EXISTS staging.stg_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    city VARCHAR(255),
    created_at TIMESTAMP
);

-- Таблица заказов
CREATE TABLE IF NOT EXISTS staging.stg_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    quantity INTEGER,
    unit_price NUMERIC(10,2),
    currency VARCHAR(10),
    order_timestamp TIMESTAMP,
    status VARCHAR(50)
);

-- Таблица товаров
CREATE TABLE IF NOT EXISTS staging.stg_products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(100),
    price NUMERIC(10,2),
    currency VARCHAR(10),
    is_active BOOLEAN
);

-- Таблица платежей
CREATE TABLE IF NOT EXISTS staging.stg_payments (
    payment_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50),
    payment_method VARCHAR(50),
    amount NUMERIC(10,2),
    currency VARCHAR(10),
    payment_timestamp TIMESTAMP
);

-- Таблица событий
CREATE TABLE IF NOT EXISTS staging.stg_events (
    event_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    event_type VARCHAR(50),
    event_timestamp TIMESTAMP,
    product_id VARCHAR(50)
);

-- Таблица для логирования ошибок качества
CREATE TABLE IF NOT EXISTS staging.error_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50),
    record_id VARCHAR(50),
    error_message TEXT,
    error_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data JSONB   -- сохраняем проблемную строку в JSON (опционально)
);