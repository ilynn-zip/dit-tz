import os
import sys
import pandas as pd
from sqlalchemy import text
from src.utils.db_conn import get_engine

def parse_sql_file(filepath):
    """Разбивает SQL-файл на отдельные запросы по ;"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    statements = []
    current = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == '':
            continue
        # Пропускаем комментарии (кроме специальных -- filename:)
        if stripped.startswith('--') and not stripped.startswith('-- filename:'):
            continue
        if stripped.startswith('\\echo'):
            continue
        current.append(line)
        if stripped.endswith(';'):
            statements.append('\n'.join(current))
            current = []
    if current:
        statements.append('\n'.join(current))
    return statements

def get_query_name(sql, idx):
    """Определяет имя для CSV-файла."""
    # Ищем специальный комментарий -- filename:
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith('-- filename:'):
            name = stripped.split('filename:')[1].strip()
            if not name.endswith('.csv'):
                name += '.csv'
            return name
    # По умолчанию используем номер запроса
    return f'query_{idx}.csv'

def main(sql_file='sql/analytics.sql', output_dir='reports'):
    if not os.path.exists(sql_file):
        print(f"Файл {sql_file} не найден.")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    statements = parse_sql_file(sql_file)
    if not statements:
        print("Нет запросов для выполнения.")
        return
    
    engine = get_engine()
    
    with engine.connect() as conn:
        for idx, stmt in enumerate(statements, 1):
            if not stmt.strip():
                continue
            print(f"--- Выполнение запроса {idx} ---")
            try:
                result = conn.execute(text(stmt))
                if result.returns_rows:
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    if not df.empty:
                        filename = get_query_name(stmt, idx)
                        filepath = os.path.join(output_dir, filename)
                        df.to_csv(filepath, index=False, encoding='utf-8-sig')
                        print(f"Сохранено {len(df)} строк в {filepath}")
                    else:
                        print("Запрос вернул пустой результат (0 строк).")
                else:
                    print("Запрос не возвращает данных (например, DDL).")
            except Exception as e:
                print(f"ОШИБКА при выполнении запроса:\n{e}")
            print("-" * 80)

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        sql_file = sys.argv[1]
    else:
        sql_file = 'sql/analytics.sql'
    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        output_dir = 'reports'
    main(sql_file, output_dir)