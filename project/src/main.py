import logging
from src.etl.extract import extract_all
from src.etl.transform import clean_customers, clean_orders, clean_products, clean_payments, clean_events
from src.etl.load import load_to_staging
from src.quality.validator import validate_customers, validate_orders, validate_payments, validate_events, log_errors
from src.utils.db_conn import get_engine
from src.dwh.load import DWHLoader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_etl():
    engine = get_engine()
    logging.info("Начало ETL")
    
    # 1. Извлечение
    raw = extract_all("data/raw/")
    if not raw:
        logging.error("Нет данных для загрузки")
        return
    
    # 2. Трансформация
    cleaned = {}
    if 'customers' in raw:
        cleaned['customers'] = clean_customers(raw['customers'])
    if 'orders' in raw:
        cleaned['orders'] = clean_orders(raw['orders'])
    if 'products' in raw:
        cleaned['products'] = clean_products(raw['products'])
    if 'payments' in raw:
        cleaned['payments'] = clean_payments(raw['payments'])
    if 'events' in raw:
        cleaned['events'] = clean_events(raw['events'])
    
    # 3. Загрузка в staging
    for name, df in cleaned.items():
        table_name = f"stg_{name}"
        load_to_staging(df, table_name, engine, if_exists='replace')
    
    # 4. Data Quality Validation
    logging.info("Запуск проверки качества данных")
    all_errors = []
    if 'customers' in cleaned:
        all_errors.extend(validate_customers(cleaned['customers'], engine))
    if 'orders' in cleaned and 'customers' in cleaned:
        all_errors.extend(validate_orders(cleaned['orders'], cleaned['customers'], engine))
    if 'payments' in cleaned and 'orders' in cleaned:
        all_errors.extend(validate_payments(cleaned['payments'], cleaned['orders'], engine))
    if 'events' in cleaned and 'customers' in cleaned:
        all_errors.extend(validate_events(cleaned['events'], cleaned['customers'], engine))
    
    # Логирование ошибок
    log_errors(all_errors, engine)
    
    # 5. Загрузка DWH
    loader = DWHLoader()
    loader.load_all()

    logging.info("ETL завершён")

if __name__ == "__main__":
    run_etl()