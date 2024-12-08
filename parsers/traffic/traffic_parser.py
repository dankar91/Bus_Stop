from tensorflow.keras.models import load_model
import tensorflow as tf
import os
from keras.preprocessing import image
import numpy as np
import cv2
from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from time import sleep

model = load_model('busstop_project/parsers/traffic/gfgModel.h5')
img_height = 180
img_width = 180
class_names = ['0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9']


opts = FirefoxOptions()
opts.add_argument("--headless")
driver = webdriver.Firefox(options=opts)


import psycopg2
from config import host, user, password, db_name

def traffic():
    driver.get("https://yandex.ru/maps/65/novosibirsk/probki/?ll=82.920430%2C55.030199&source=traffic&z=12")
    sleep(5)
    driver.save_screenshot('busstop_project/parsers/traffic/screenie.png')
    img = cv2.imread("busstop_project/parsers/traffic/screenie.png")
    crop_img = img[120:170, 0:200]
    cv2.imwrite("busstop_project/parsers/traffic/croped_scr.png", crop_img)

    img = image.load_img  (
     'busstop_project/parsers/traffic/croped_scr.png', target_size=(img_height, img_width)
    )
    img_array = image.img_to_array(img)
    img_array = tf.expand_dims(img_array, 0)

    predictions = model.predict(img_array)
    score = tf.nn.softmax(predictions[0])

    print(
        "This image most likely belongs to {} with a {:.2f} percent confidence."
        .format(class_names[np.argmax(score)], 100 * np.max(score))
    )
    traffic_point = class_names[np.argmax(score)]
    city = 'Новосибирск'
    print(city, traffic_point)

    try:
        # Присоединение к базе данных
        connection = psycopg2.connect(
            host = host,
            user = user,
            password = password,
            database = db_name,   
            port = '5434'
        )
        connection.autocommit = True
    
        cursor = connection.cursor()
 
        # Определение запроса с несколькими переменными
        query = 'INSERT INTO public."Traffic" VALUES (NOW(), %s, %s)'
 
        # Создание списка переменных
        data = (city, traffic_point)
 
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

traffic()