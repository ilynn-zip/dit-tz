import logging

def load_to_staging(df, table_name, engine, schema='staging', if_exists='replace'):
    if df.empty:
        logging.warning(f"DataFrame для {table_name} пуст, загрузка пропущена")
        return
    try:
        df.to_sql(table_name, engine, schema=schema, if_exists=if_exists, index=False, method='multi')
        logging.info(f"Загружено {len(df)} записей в {schema}.{table_name}")
    except Exception as e:
        logging.error(f"Ошибка загрузки в {schema}.{table_name}: {e}")
        raise