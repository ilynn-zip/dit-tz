import pandas as pd
import pytest
from datetime import datetime
from src.etl.transform import (
    standardize_columns,
    clean_customers,
    clean_orders,
    clean_payments,
    clean_events,
    safe_convert_datetime,
    safe_convert_numeric,
    clean_id
)

# -------------------------------------------------------------------
# Тесты для вспомогательных функций
# -------------------------------------------------------------------

def test_standardize_columns():
    df = pd.DataFrame({
        'Customer ID': [1, 2],
        'Full Name': ['A', 'B'],
        '  Email  ': ['a@b', 'c@d']
    })
    df = standardize_columns(df)
    assert 'customer_id' in df.columns
    assert 'full_name' in df.columns
    assert 'email' in df.columns

def test_safe_convert_datetime():
    series = pd.Series(['2025-01-01', '2025-99-99', 'invalid', None])
    result = safe_convert_datetime(series)
    assert pd.isna(result[1])  # битая дата -> NaT
    assert pd.isna(result[2])  # invalid -> NaT
    assert pd.isna(result[3])  # None -> NaT
    assert isinstance(result[0], pd.Timestamp)

def test_safe_convert_numeric():
    series = pd.Series(['123', 'error_amount', 'N/A', '456.78', None])
    result = safe_convert_numeric(series)
    assert result[0] == 123.0
    assert pd.isna(result[1])  # error_amount -> NaN
    assert pd.isna(result[2])  # N/A -> NaN
    assert result[3] == 456.78
    assert pd.isna(result[4])  # None -> NaN

def test_clean_id():
    # Числовые значения
    assert clean_id(123) == '123'
    assert clean_id(123.0) == '123'
    assert clean_id('123.0') == '123'
    assert clean_id('123') == '123'
    # Строковые
    assert clean_id('  456  ') == '456'
    # None / NaN
    assert pd.isna(clean_id(None))
    assert pd.isna(clean_id(float('nan')))

# -------------------------------------------------------------------
# Тесты для clean_customers
# -------------------------------------------------------------------

def test_clean_customers_standardization():
    df = pd.DataFrame({
        'customer_id': [1, 2],
        'full_name': ['  Ivan  ', 'Petr  '],
        'email': ['  TEST@MAIL.RU', '   other@mail.com '],
        'created_at': ['2025-01-01', '2024-12-31']
    })
    result = clean_customers(df)
    # Проверяем переименование колонок
    assert 'customer_id' in result.columns
    assert 'full_name' in result.columns
    assert 'email' in result.columns
    assert 'created_at' in result.columns
    # Проверяем стандартизацию строк
    assert result['full_name'].iloc[0] == 'Ivan'
    assert result['email'].iloc[0] == 'test@mail.ru'
    # Проверяем даты
    assert isinstance(result['created_at'].iloc[0], pd.Timestamp)

def test_clean_customers_deduplication():
    df = pd.DataFrame({
        'customer_id': [1, 1, 2],
        'full_name': ['A', 'B', 'C']
    })
    result = clean_customers(df)
    # Должно остаться 2 записи (customer_id=1 и 2)
    assert len(result) == 2
    # Оставлена первая запись для дубликата
    assert result['full_name'].iloc[0] == 'A'

def test_clean_customers_missing_required():
    df = pd.DataFrame({
        'customer_id': [1, None, 2],
        'full_name': ['A', 'B', 'C']
    })
    result = clean_customers(df)
    # Строка с None в customer_id удаляется
    assert len(result) == 2
    assert result['customer_id'].iloc[0] == '1'
    assert result['customer_id'].iloc[1] == '2'

def test_clean_customers_invalid_date():
    df = pd.DataFrame({
        'customer_id': [1, 2],
        'full_name': ['A', 'B'],
        'created_at': ['2025-99-99', '2024-01-01']
    })
    result = clean_customers(df)
    # Первая дата станет NaT
    assert pd.isna(result['created_at'].iloc[0])
    # Вторая останется валидной
    assert isinstance(result['created_at'].iloc[1], pd.Timestamp)

# -------------------------------------------------------------------
# Тесты для clean_orders
# -------------------------------------------------------------------

def test_clean_orders_required_fields():
    df = pd.DataFrame({
        'order_id': [1, 2, 3],
        'product_id': ['A', 'B', None],
        'order_timestamp': ['2025-01-01', '2025-01-02', '2025-01-03'],
        'quantity': [1, 2, 3],
        'unit_price': [10, 20, 30]
    })
    result = clean_orders(df)
    # Третья запись должна быть удалена (product_id None)
    assert len(result) == 2
    assert result['order_id'].iloc[0] == '1'
    assert result['order_id'].iloc[1] == '2'

def test_clean_orders_negative_values():
    df = pd.DataFrame({
        'order_id': [1, 2],
        'product_id': ['A', 'B'],
        'order_timestamp': ['2025-01-01', '2025-01-02'],
        'quantity': [-1, 5],
        'unit_price': [10, -5]
    })
    result = clean_orders(df)
    # Обе строки должны быть удалены (отрицательные значения)
    assert len(result) == 0

def test_clean_orders_bad_date():
    df = pd.DataFrame({
        'order_id': [1, 2],
        'product_id': ['A', 'B'],
        'order_timestamp': ['2025-99-99', '2025-01-02']
    })
    result = clean_orders(df)
    # Первая строка удаляется (битая дата)
    assert len(result) == 1
    assert result['order_id'].iloc[0] == '2'

def test_clean_orders_deduplication():
    df = pd.DataFrame({
        'order_id': [1, 1, 2],
        'product_id': ['A', 'B', 'C'],
        'order_timestamp': ['2025-01-01', '2025-01-01', '2025-01-02']
    })
    result = clean_orders(df)
    assert len(result) == 2

def test_clean_orders_currency_case():
    df = pd.DataFrame({
        'order_id': [1],
        'product_id': ['A'],
        'order_timestamp': ['2025-01-01'],
        'currency': ['usd']
    })
    result = clean_orders(df)
    assert result['currency'].iloc[0] == 'USD'

# -------------------------------------------------------------------
# Тесты для clean_payments
# -------------------------------------------------------------------

def test_clean_payments_error_amount():
    df = pd.DataFrame({
        'payment_id': [1, 2],
        'amount': ['error_amount', 100],
        'payment_timestamp': ['2025-01-01', '2025-01-02']
    })
    result = clean_payments(df)
    # Первая строка удалена (amount не число)
    assert len(result) == 1
    assert result['payment_id'].iloc[0] == '2'

def test_clean_payments_negative_amount():
    df = pd.DataFrame({
        'payment_id': [1, 2],
        'amount': [-50, 100],
        'payment_timestamp': ['2025-01-01', '2025-01-02']
    })
    result = clean_payments(df)
    # Первая строка удалена (отрицательная сумма)
    assert len(result) == 1
    assert result['payment_id'].iloc[0] == '2'

def test_clean_payments_missing_timestamp():
    df = pd.DataFrame({
        'payment_id': [1, 2],
        'amount': [100, 200],
        'payment_timestamp': [None, '2025-01-02']
    })
    result = clean_payments(df)
    assert len(result) == 1
    assert result['payment_id'].iloc[0] == '2'

# -------------------------------------------------------------------
# Тесты для clean_events
# -------------------------------------------------------------------

def test_clean_events_bad_id():
    df = pd.DataFrame({
        'event_id': [1, 'BAD_ID', 3],
        'event_timestamp': ['2025-01-01', '2025-01-02', '2025-01-03']
    })
    result = clean_events(df)
    # 'BAD_ID' удалено
    assert len(result) == 2
    assert 'BAD_ID' not in result['event_id'].values

def test_clean_events_missing_timestamp():
    df = pd.DataFrame({
        'event_id': [1, 2],
        'event_timestamp': [None, '2025-01-02']
    })
    result = clean_events(df)
    assert len(result) == 1
    assert result['event_id'].iloc[0] == '2'

def test_clean_events_duplicate():
    df = pd.DataFrame({
        'event_id': [1, 1, 2],
        'event_timestamp': ['2025-01-01', '2025-01-01', '2025-01-02']
    })
    result = clean_events(df)
    assert len(result) == 2