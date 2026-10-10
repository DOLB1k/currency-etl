import os
import json
import boto3
import pandas as pd
import great_expectations as gx
from botocore.client import Config
from io import BytesIO


def transform_and_validate_data(**kwargs):
    ti = kwargs['ti']
    s3_uri = ti.xcom_pull(task_ids='extract_task')

    bucket_name = s3_uri.split('/')[2]
    object_key = '/'.join(s3_uri.split('/')[3:])

    minio_endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    s3_client = boto3.client(
        's3', endpoint_url=f'http://{minio_endpoint}',
        aws_access_key_id=os.getenv('MINIO_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('MINIO_SECRET_KEY'),
        config=Config(signature_version='s3v4'), region_name='us-east-1'
    )

    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    raw_data = json.loads(response['Body'].read().decode('utf-8'))

    rates = raw_data.get('rates', {})
    base_currency = raw_data.get('base', 'USD')
    time_last_update = raw_data.get('time_last_update_utc')

    df = pd.DataFrame(list(rates.items()), columns=['currency_code', 'rate'])
    df['base_currency'] = base_currency
    df['rate_date'] = pd.to_datetime(time_last_update).date()
    df['load_timestamp'] = pd.to_datetime('now')

    df['rate'] = pd.to_numeric(df['rate'], errors='coerce')
    df.dropna(subset=['rate'], inplace=True)

    print("Running Great Expectations validation...")
    df_ge = gx.from_pandas(df)

    df_ge.expect_column_values_to_not_be_null('currency_code')
    df_ge.expect_column_values_to_not_be_null('rate')
    df_ge.expect_column_values_to_be_between('rate', min_value=0.001, max_value=100000.0)
    df_ge.expect_column_values_to_be_unique('currency_code')

    validation_result = df_ge.validate()

    if not validation_result['success']:
        failed_stats = validation_result.get('statistics', {})
        raise ValueError(f"Data Quality Check Failed! Unsuccessful expectations: {failed_stats}")

    print("Data Quality Check Passed.")

    ti.xcom_push(key='transformed_df', value=df.to_json(orient='records'))
    return "Transformation and validation completed successfully."