import os
import json
import requests
import boto3
from datetime import datetime
from botocore.client import Config


def extract_currency_data(**kwargs):
    minio_endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minio_admin')
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minio_pass')
    bucket_name = 'raw-currency-data'

    s3_client = boto3.client(
        's3',
        endpoint_url=f'http://{minio_endpoint}',
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

    try:
        s3_client.create_bucket(Bucket=bucket_name)
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        pass

    api_url = 'https://open.er-api.com/v6/latest/USD'
    print(f"Fetching data from {api_url}...")

    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    raw_data = response.json()

    raw_data['extraction_timestamp'] = datetime.utcnow().isoformat()
    raw_data['source_api'] = 'open.er-api.com'

    execution_date = kwargs.get('ds', datetime.utcnow().strftime('%Y-%m-%d'))
    year, month, day = execution_date.split('-')

    object_key = f"currency_rates/year={year}/month={month}/day={day}/data.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=json.dumps(raw_data, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json'
    )

    print(f"Successfully extracted and saved data to s3://{bucket_name}/{object_key}")
    return f"s3://{bucket_name}/{object_key}"