import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import psycopg2
from config import host, user, password, db_name

bus_route_dict = {'14 автобус':1, '6 автобус':12, '8 троллейбус':14, '4 троллейбус':13,  '68 автобус':4, '88 автобус':5, '16 автобус':6, 
                  '7 троллейбус':7, '45 автобус':8, '63 маршрутное такси':9}



def bus_arrival():
    url = 'https://maps.nskgortrans.ru/qr_code/qr_forecast_2.php?id=30'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')
        
    buses = []
    arrival = []

    for t in soup.find_all('td'):
        buses.append(t.text)

    for i in range(len(buses)):
        if buses[i] == ' прибытие ':
            arrival = buses[i-1]
            print(arrival)
    if arrival != []:
         
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

            bus_stop_id = 14

            route_id = bus_route_dict[arrival]

            route_name = arrival
 
            # Определение запроса с несколькими переменными
            query = 'INSERT INTO public."Bus_arrival" VALUES (NOW(), %s, %s, %s)'
 
            # Создание списка переменных
            data = (bus_stop_id, route_id, route_name)
 
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
    else:
        print('Транспорт не пришел')

bus_arrival()

