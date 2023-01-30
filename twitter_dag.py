from datetime import timedelta, datetime
from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator
from main import run_twitter_etl

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email': ['test@email.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=3)
}

dag = DAG(
    'twitter_dag',
    default_args=default_args,
    description='Get financial news from tt'
)

run_etl = PythonOperator(
    task_id='perform_twitter_etl',
    python_callable=run_twitter_etl,
    dag=dag,
)
