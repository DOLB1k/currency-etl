from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

from extract import extract_currency_data
from transform import transform_and_validate_data
from load import load_to_dwh

default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2023, 1, 1),
}

with DAG(
    'currency_etl_pipeline',
    default_args=default_args,
    description='Batch ETL pipeline for currency rates analysis',
    schedule_interval='@daily',
    catchup=False,
    tags=['finance', 'etl', 'currency'],
) as dag:

    extract_task = PythonOperator(
        task_id='extract_task',
        python_callable=extract_currency_data,
        provide_context=True,
    )

    transform_task = PythonOperator(
        task_id='transform_task',
        python_callable=transform_and_validate_data,
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id='load_task',
        python_callable=load_to_dwh,
        provide_context=True,
    )

    extract_task >> transform_task >> load_task