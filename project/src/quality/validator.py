import logging
import pandas as pd
from sqlalchemy import text

def validate_customers(df, engine):
    """Проверка клиентов: дубликаты, пропуски обязательных полей, формат email."""
    errors = []
    # Проверка на дубликаты (уже удалены, но проверим)
    duplicates = df[df.duplicated(subset=['customer_id'], keep=False)]
    if not duplicates.empty:
        for _, row in duplicates.iterrows():
            errors.append({
                'table_name': 'stg_customers',
                'record_id': row['customer_id'],
                'error_message': f"Duplicate customer_id: {row['customer_id']}",
                'raw_data': row.to_json()
            })
    # Проверка email (простая: содержит @)
    invalid_email = df[~df['email'].str.contains('@', na=False)]
    if not invalid_email.empty:
        for _, row in invalid_email.iterrows():
            errors.append({
                'table_name': 'stg_customers',
                'record_id': row['customer_id'],
                'error_message': f"Invalid email: {row['email']}",
                'raw_data': row.to_json()
            })
    return errors

def validate_orders(df, df_customers, engine):
    """Проверка заказов: внешние ключи на customers, отрицательные суммы."""
    errors = []
    valid_customer_ids = set(df_customers['customer_id'].dropna())
    # Проверка customer_id
    invalid_customer = df[~df['customer_id'].isin(valid_customer_ids) & df['customer_id'].notna()]
    if not invalid_customer.empty:
        for _, row in invalid_customer.iterrows():
            errors.append({
                'table_name': 'stg_orders',
                'record_id': row['order_id'],
                'error_message': f"customer_id {row['customer_id']} not found in customers",
                'raw_data': row.to_json()
            })
    # Проверка отрицательной суммы (хотя уже очищено, но на всякий случай)
    negative_amount = df[df['unit_price'] < 0]
    if not negative_amount.empty:
        for _, row in negative_amount.iterrows():
            errors.append({
                'table_name': 'stg_orders',
                'record_id': row['order_id'],
                'error_message': f"Negative unit_price: {row['unit_price']}",
                'raw_data': row.to_json()
            })
    return errors

def validate_payments(df, df_orders, engine):
    """Проверка платежей: внешние ключи на orders, отрицательные суммы."""
    errors = []
    valid_order_ids = set(df_orders['order_id'].dropna())
    invalid_order = df[~df['order_id'].isin(valid_order_ids) & df['order_id'].notna()]
    if not invalid_order.empty:
        for _, row in invalid_order.iterrows():
            errors.append({
                'table_name': 'stg_payments',
                'record_id': row['payment_id'],
                'error_message': f"order_id {row['order_id']} not found in orders",
                'raw_data': row.to_json()
            })
    negative_amount = df[df['amount'] < 0]
    if not negative_amount.empty:
        for _, row in negative_amount.iterrows():
            errors.append({
                'table_name': 'stg_payments',
                'record_id': row['payment_id'],
                'error_message': f"Negative amount: {row['amount']}",
                'raw_data': row.to_json()
            })
    return errors

def validate_events(df, df_customers, engine):
    """Проверка событий: внешние ключи на customers."""
    errors = []
    valid_customer_ids = set(df_customers['customer_id'].dropna())
    invalid_customer = df[~df['customer_id'].isin(valid_customer_ids) & df['customer_id'].notna()]
    if not invalid_customer.empty:
        for _, row in invalid_customer.iterrows():
            errors.append({
                'table_name': 'stg_events',
                'record_id': row['event_id'],
                'error_message': f"customer_id {row['customer_id']} not found in customers",
                'raw_data': row.to_json()
            })
    return errors

def log_errors(errors, engine):
    """Записывает ошибки в таблицу staging.error_log."""
    if not errors:
        logging.info("No errors to log.")
        return
    df_errors = pd.DataFrame(errors)
    # Если таблица error_log уже существует, добавляем строки
    try:
        df_errors.to_sql('error_log', engine, schema='staging', if_exists='append', index=False)
        logging.info(f"Logged {len(errors)} errors to staging.error_log.")
    except Exception as e:
        logging.error(f"Failed to log errors: {e}")