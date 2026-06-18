import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

def read_csv(file_path, **kwargs):
    try:
        return pd.read_csv(file_path, encoding='utf-8', **kwargs)
    except Exception as e:
        logging.error(f"Ошибка чтения CSV {file_path}: {e}")
        return None

def read_json(file_path, **kwargs):
    try:
        return pd.read_json(file_path, **kwargs)
    except Exception as e:
        logging.error(f"Ошибка чтения JSON {file_path}: {e}")
        return None

def read_xlsx(file_path, **kwargs):
    try:
        return pd.read_excel(file_path, **kwargs)
    except Exception as e:
        logging.error(f"Ошибка чтения XLSX {file_path}: {e}")
        return None

def read_xml(file_path, **kwargs):
    try:
        return pd.read_xml(file_path, **kwargs)
    except Exception as e:
        logging.error(f"Ошибка чтения XML {file_path}: {e}")
        return None

def extract_all(data_dir="data/raw/"):
    files = {
        'customers': Path(data_dir) / 'customers.csv',
        'orders': Path(data_dir) / 'orders.json',
        'products': Path(data_dir) / 'products.xlsx',
        'payments': Path(data_dir) / 'payments.csv',
        'events': Path(data_dir) / 'events.xml'
    }
    data = {}
    for name, path in files.items():
        if not path.exists():
            logging.warning(f"Файл {path} не найден")
            continue
        if name == 'customers':
            df = read_csv(path)
        elif name == 'orders':
            df = read_json(path)
        elif name == 'products':
            df = read_xlsx(path, sheet_name='products')
        elif name == 'payments':
            df = read_csv(path, sep='^')
        elif name == 'events':
            df = read_xml(path, xpath='.//event')
        else:
            continue
        if df is not None and not df.empty:
            data[name] = df
            logging.info(f"Загружено {len(df)} строк из {path.name}")
        else:
            logging.warning(f"Не удалось загрузить {path.name}")
    return data