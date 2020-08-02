import requests

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils import timezone

import pandas


default_args = {
    'owner': 'thoritie',
}

dag = DAG('product_price_pipeline',
    default_args=default_args,
    start_date=timezone.datetime(2020,8,1),
    catchup=False
    )

start = DummyOperator(task_id='start', dag=dag)


def get_product_upc_and_description():
    df = pandas.read_csv('./dataset/products-lookup-table.csv', header=1)
    new_df = df[['UPC', 'DESCRIPTION']]
    new_df.to_csv('./dataset/product_upc_and_description.csv', index=False)

def remove_outliers():
    df = pandas.read_csv('./dataset/transactions.csv', header=1)
    valid_data = df['UNITS'] >= df['VISITS']
    new_df = df[valid_data]
    new_df.to_csv('./dataset/cleaned_transactions.csv', index=False)

remove_outliers = PythonOperator(
    task_id='remove_outliers',
    python_callable=remove_outliers,
    dag=dag
)


def get_upc_and_price():
    df = pandas.read_csv('./dataset/cleaned_transactions.csv', header=0)
    new_df = df[['UPC', 'PRICE']]
    new_df.to_csv('./dataset/upc_and_price.csv', index=False)

def merge():
    df_product_description = pandas.read_csv('./dataset/product_upc_and_description.csv')
    df_product_price = pandas.read_csv('./dataset/upc_and_price.csv')

    new_df = pandas.merge(df_product_description, df_product_price, left_on='UPC', right_on='UPC')
    # new_df = df_product_description.join(df_product_price, on='UPC', how='left')
    new_df.to_csv('./dataset/product_and_price.csv', index=False)

get_product_upc_and_description = PythonOperator(
    task_id='get_product_upc_and_description',
    python_callable=get_product_upc_and_description,
    dag=dag
)

get_upc_and_price = PythonOperator(
    task_id='get_upc_and_price',
    python_callable=get_upc_and_price,
    dag=dag
)

merge = PythonOperator(
    task_id='merge',
    python_callable=merge,
    dag=dag
)

def include_vat():
    df = pandas.read_csv('./dataset/product_and_price.csv')
    df['PRICE_WITH_VAT'] = df['PRICE'] * 1.08
    df.to_csv('./dataset/product_and_price_with_vat.csv', index=False)

include_vat = PythonOperator(
    task_id='include_vat',
    python_callable=include_vat,
    dag=dag
)

end = DummyOperator(task_id='end', dag=dag)

start >> [get_product_upc_and_description, remove_outliers]
get_product_upc_and_description >> merge
remove_outliers >> get_upc_and_price >> merge
merge >> include_vat >> end