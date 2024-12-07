import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import psycopg2
from config import host, user, password, db_name

def weather():

    url = 'https://pogoda.mail.ru/prognoz/novosibirsk/'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')
    temperature = soup.find('div', class_= 'information__content__temperature').text
    temperature = int(temperature[1:-9])
    condition = soup.find('div', class_= 'information__content__additional information__content__additional_first').find('div', class_= 'information__content__additional__item').text
    condition = condition[9:-8]
    city = 'Новосибирск'
    print(city, temperature, condition)

    try:
        # Присоединение к базе данных
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name,   
            port='5434'
        )
        connection.autocommit = True
    
        cursor = connection.cursor()
 
        # Определение запроса с несколькими переменными
        query = 'INSERT INTO public."Weather" VALUES (NOW(), %s, %s, %s)'
 
        # Создание списка переменных
        data = (temperature, condition, city)
 
        # Выполнение запроса
        cursor.execute(query, data)
        
        print("[INFO] Data was succefully inserted")

        cursor.close()
     
           
    except Exception as _ex:
        print("[INFO] Error while working with PostgreSQL", _ex)
    finally:
        if connection:
            connection.close()
            print("[INFO] PostgreSQL connection closed")


weather()