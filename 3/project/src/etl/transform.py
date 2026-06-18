import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def standardize_columns(df):
    """
    приводит названия колонок к нижнему регистру
    заменяет пробелы на подчёркивания
    """
    df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
    return df

def safe_convert_datetime_old(series):
    """
    конвертирует в datetime
    некорректные значения в NaT
    """
    return pd.to_datetime(series, errors='coerce', infer_datetime_format=True)

def safe_convert_datetime(series):
    """
    конвертирует в datetime
    некорректные значения в NaT
    """
    return pd.to_datetime(series, errors='coerce', format='mixed')

def safe_convert_numeric(series):
    """
    конвертирует в число
    заменяет 'error_amount', 'N/A', 'NA', '' на NaN
    """
    series = series.replace(['error_amount', 'N/A', 'NA', 'null', ''], pd.NA)
    return pd.to_numeric(series, errors='coerce')

def clean_id(value):
    """
    приводит идентификатор к строке без десятичной точки
     – число (int или float), преобразует его в int и затем в str
     – строка, обрезает пробелы и возвращает как есть
     – None или NaN, возвращает pd.NA
    """
    if pd.isna(value):
        return pd.NA
    try:
        return str(int(float(value)))
    except (ValueError, TypeError):
        return str(value).strip()

def clean_customers(df):
    df = df.copy()
    df = standardize_columns(df)
    initial_count = len(df)

    rename_map = {
        'customer_id': 'customer_id',
        'full_name': 'full_name',
        'email': 'email',
        'phone': 'phone',
        'city': 'city',
        'created_at': 'created_at'
    }
    df.rename(columns=rename_map, inplace=True)

    if 'customer_id' in df.columns:
        df['customer_id'] = df['customer_id'].apply(clean_id)
    if 'full_name' in df.columns:
        df['full_name'] = df['full_name'].astype(str).str.strip().replace('', pd.NA)
    if 'email' in df.columns:
        df['email'] = df['email'].astype(str).str.lower().str.strip().replace('', pd.NA)
    if 'phone' in df.columns:
        df['phone'] = df['phone'].astype(str).str.strip().replace('', pd.NA)
    if 'city' in df.columns:
        df['city'] = df['city'].astype(str).str.strip().replace('', pd.NA)
    if 'created_at' in df.columns:
        df['created_at'] = safe_convert_datetime(df['created_at'])

    if 'customer_id' in df.columns:
        df.drop_duplicates(subset=['customer_id'], keep='first', inplace=True)

    df.dropna(subset=['customer_id'], inplace=True)

    logging.info(f"Customers: загружено {len(df)} записей (было {initial_count}, отброшено {initial_count - len(df)})")
    return df

def clean_orders(df):
    df = df.copy()
    df = standardize_columns(df)
    initial_count = len(df)

    rename_map = {
        'order_id': 'order_id',
        'customer_id': 'customer_id',
        'product_id': 'product_id',
        'quantity': 'quantity',
        'unit_price': 'unit_price',
        'currency': 'currency',
        'order_timestamp': 'order_timestamp',
        'status': 'status'
    }
    df.rename(columns=rename_map, inplace=True)

    if 'order_id' in df.columns:
        df['order_id'] = df['order_id'].apply(clean_id)
    if 'customer_id' in df.columns:
        df['customer_id'] = df['customer_id'].apply(clean_id)
    else:
        df['customer_id'] = pd.NA
    if 'product_id' in df.columns:
        df['product_id'] = df['product_id'].apply(clean_id)
    if 'quantity' in df.columns:
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    if 'unit_price' in df.columns:
        df['unit_price'] = safe_convert_numeric(df['unit_price'])
    if 'currency' in df.columns:
        df['currency'] = df['currency'].astype(str).str.upper().str.strip().replace('', pd.NA)
    if 'order_timestamp' in df.columns:
        df['order_timestamp'] = safe_convert_datetime(df['order_timestamp'])
    if 'status' in df.columns:
        df['status'] = df['status'].astype(str).str.strip().replace('', pd.NA)

    if 'order_id' in df.columns:
        df.drop_duplicates(subset=['order_id'], keep='first', inplace=True)

    required = ['order_id', 'product_id', 'order_timestamp']
    df.dropna(subset=required, inplace=True)

    if 'quantity' in df.columns:
        df = df[df['quantity'] >= 0]
    if 'unit_price' in df.columns:
        df = df[df['unit_price'] >= 0]

    logging.info(f"Orders: загружено {len(df)} записей (было {initial_count}, отброшено {initial_count - len(df)})")
    return df

def clean_products(df):
    df = df.copy()
    df = standardize_columns(df)
    initial_count = len(df)

    rename_map = {
        'product_id': 'product_id',
        'product_name': 'product_name',
        'category': 'category',
        'price': 'price',
        'currency': 'currency',
        'is_active': 'is_active'
    }
    df.rename(columns=rename_map, inplace=True)

    if 'product_id' in df.columns:
        df['product_id'] = df['product_id'].apply(clean_id)
    if 'product_name' in df.columns:
        df['product_name'] = df['product_name'].astype(str).str.strip().replace('', pd.NA)
    if 'category' in df.columns:
        df['category'] = df['category'].astype(str).str.strip().replace('', pd.NA)
    if 'price' in df.columns:
        df['price'] = safe_convert_numeric(df['price'])
    if 'currency' in df.columns:
        df['currency'] = df['currency'].astype(str).str.upper().str.strip().replace('', pd.NA)
    if 'is_active' in df.columns:
        df['is_active'] = df['is_active'].astype(str).str.lower().map(
            {'true': True, 'false': False, '1': True, '0': False, 't': True, 'f': False}
        ).fillna(False)

    if 'product_id' in df.columns:
        df.drop_duplicates(subset=['product_id'], keep='first', inplace=True)

    required = ['product_id', 'product_name']
    df.dropna(subset=required, inplace=True)

    logging.info(f"Products: загружено {len(df)} записей (было {initial_count}, отброшено {initial_count - len(df)})")
    return df

def clean_payments(df):
    df = df.copy()
    df = standardize_columns(df)
    initial_count = len(df)

    rename_map = {
        'payment_id': 'payment_id',
        'order_id': 'order_id',
        'payment_method': 'payment_method',
        'amount': 'amount',
        'currency': 'currency',
        'payment_timestamp': 'payment_timestamp'
    }
    df.rename(columns=rename_map, inplace=True)

    if 'payment_id' in df.columns:
        df['payment_id'] = df['payment_id'].apply(clean_id)
    if 'order_id' in df.columns:
        df['order_id'] = df['order_id'].apply(clean_id)
    if 'payment_method' in df.columns:
        df['payment_method'] = df['payment_method'].astype(str).str.strip().replace('', pd.NA)
    if 'amount' in df.columns:
        df['amount'] = safe_convert_numeric(df['amount'])
    if 'currency' in df.columns:
        df['currency'] = df['currency'].astype(str).str.upper().str.strip().replace('', pd.NA)
    if 'payment_timestamp' in df.columns:
        df['payment_timestamp'] = safe_convert_datetime(df['payment_timestamp'])

    if 'payment_id' in df.columns:
        df.drop_duplicates(subset=['payment_id'], keep='first', inplace=True)

    required = ['payment_id', 'amount', 'payment_timestamp']
    df.dropna(subset=required, inplace=True)

    if 'amount' in df.columns:
        df = df[df['amount'] >= 0]

    logging.info(f"Payments: загружено {len(df)} записей (было {initial_count}, отброшено {initial_count - len(df)})")
    return df

def clean_events(df):
    df = df.copy()
    df = standardize_columns(df)
    initial_count = len(df)

    rename_map = {
        'event_id': 'event_id',
        'customer_id': 'customer_id',
        'event_type': 'event_type',
        'event_timestamp': 'event_timestamp',
        'product_id': 'product_id'
    }
    df.rename(columns=rename_map, inplace=True)

    if 'event_id' in df.columns:
        df = df[df['event_id'] != 'BAD_ID']
        df['event_id'] = df['event_id'].apply(clean_id)
    if 'customer_id' in df.columns:
        df['customer_id'] = df['customer_id'].apply(clean_id)
    if 'event_type' in df.columns:
        df['event_type'] = df['event_type'].astype(str).str.lower().str.strip().replace('', pd.NA)
    if 'event_timestamp' in df.columns:
        df['event_timestamp'] = safe_convert_datetime(df['event_timestamp'])
    if 'product_id' in df.columns:
        df['product_id'] = df['product_id'].apply(clean_id)

    if 'event_id' in df.columns:
        df.drop_duplicates(subset=['event_id'], keep='first', inplace=True)

    required = ['event_id', 'event_timestamp']
    df.dropna(subset=required, inplace=True)

    logging.info(f"Events: загружено {len(df)} записей (было {initial_count}, отброшено {initial_count - len(df)})")
    return df