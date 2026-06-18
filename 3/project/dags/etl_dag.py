from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, '/opt/airflow')

from src.main import run_etl

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2026, 6, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'etl_dag',
    default_args=default_args,
    description='ETL пайплайн: загрузка, очистка, DWH, качество',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'dwh'],
)

run_etl_task = PythonOperator(
    task_id='run_full_etl',
    python_callable=run_etl,
    dag=dag,
)

run_etl_task