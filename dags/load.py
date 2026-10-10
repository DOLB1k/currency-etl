import os
import json
import pandas as pd
from sqlalchemy import create_engine, text


def load_to_dwh(**kwargs):
    ti = kwargs['ti']
    df_json = ti.xcom_pull(task_ids='transform_task', key='transformed_df')
    df = pd.read_json(df_json, orient='records')

    dwh_conn_str = os.getenv('DWH_CONNECTION_STRING',
                             'postgresql+psycopg2://dwh_user:dwh_pass@localhost:5432/currency_dwh')
    engine = create_engine(dwh_conn_str)

    create_table_query = """
    CREATE TABLE IF NOT EXISTS dim_currency_rates (
        currency_code VARCHAR(10) NOT NULL,
        base_currency VARCHAR(10) NOT NULL,
        rate NUMERIC(15, 6) NOT NULL,
        rate_date DATE NOT NULL,
        load_timestamp TIMESTAMP NOT NULL,
        PRIMARY KEY (currency_code, base_currency, rate_date)
    );
    """
    with engine.connect() as connection:
        connection.execute(text(create_table_query))
        connection.commit()

    print(f"Loading {len(df)} records to PostgreSQL DWH...")

    with engine.connect() as connection:
        for index, row in df.iterrows():
            upsert_query = text("""
                INSERT INTO dim_currency_rates (currency_code, base_currency, rate, rate_date, load_timestamp)
                VALUES (:code, :base, :rate, :date, :ts)
                ON CONFLICT (currency_code, base_currency, rate_date) 
                DO UPDATE SET 
                    rate = EXCLUDED.rate,
                    load_timestamp = EXCLUDED.load_timestamp;
            """)
            connection.execute(upsert_query, {
                'code': row['currency_code'],
                'base': row['base_currency'],
                'rate': float(row['rate']),
                'date': row['rate_date'],
                'ts': row['load_timestamp']
            })
        connection.commit()

    print("Data successfully loaded to DWH.")
    return f"Loaded {len(df)} rows."