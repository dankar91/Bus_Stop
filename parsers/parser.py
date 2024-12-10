from abc import ABC, abstractmethod
import psycopg2
from bs4 import BeautifulSoup
import requests
from config import host, user, password, db_name

class BaseParser(ABC):
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def connect_to_db(self):
        try:
            self.connection = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                database=db_name,
                port='5434'
            )
            self.connection.autocommit = True
            self.cursor = self.connection.cursor()
            return True
        except Exception as e:
            print(f"[INFO] Error connecting to PostgreSQL: {e}")
            return False
            
    def close_connection(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            
class WeatherParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.url = 'https://pogoda.mail.ru/prognoz/novosibirsk/'
        
    def parse(self):
        try:
            r = requests.get(self.url)
            soup = BeautifulSoup(r.text, 'lxml')
            temperature = soup.find('div', class_='information__content__temperature').text
            temperature = int(temperature[1:-9])
            condition = soup.find('div', class_='information__content__additional information__content__additional_first').find('div', class_='information__content__additional__item').text
            condition = condition[9:-8]
            city = 'Новосибирск'
            return {'temperature': temperature, 'condition': condition, 'city': city}
        except Exception as e:
            print(f"[INFO] Error parsing weather: {e}")
            return None
            
    def save_to_db(self, data):
        if not data:
            return False
        try:
            if self.connect_to_db():
                query = 'INSERT INTO public."Weather" VALUES (NOW(), %s, %s, %s)'
                self.cursor.execute(query, (data['temperature'], data['condition'], data['city']))
                print("[INFO] Weather data was successfully inserted")
                return True
        except Exception as e:
            print(f"[INFO] Error saving weather data: {e}")
        finally:
            self.close_connection()
        return False

class BusStopParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.url = 'https://maps.nskgortrans.ru/qr_code/qr_forecast_2.php?id=30'
        self.bus_route_dict = {'14 автобус':1, '6 автобус':12, '8 троллейбус':14, '4 троллейбус':13,  '68 автобус':4, '88 автобус':5, '16 автобус':6, 
                  '7 троллейбус':7, '45 автобус':8, '63 маршрутное такси':9}  # Словарь для маппинга маршрутов
        
    def parse(self):
        try:
            r = requests.get(self.url)
            soup = BeautifulSoup(r.text, 'lxml')
            buses = []
            arrival = []
            
            for t in soup.find_all('td'):
                buses.append(t.text)
                
            for i in range(len(buses)):
                if buses[i] == ' прибытие ':
                    arrival = buses[i-1]
            
            if arrival:
                return {
                    'bus_stop_id': 14,
                    'route_id': self.bus_route_dict.get(arrival),
                    'route_name': arrival
                }
            return None
        except Exception as e:
            print(f"[INFO] Error parsing bus stop: {e}")
            return None
            
    def save_to_db(self, data):
        if not data:
            return False
        try:
            if self.connect_to_db():
                query = 'INSERT INTO public."Bus_arrival" VALUES (NOW(), %s, %s, %s)'
                self.cursor.execute(query, (data['bus_stop_id'], data['route_id'], data['route_name']))
                print("[INFO] Bus arrival data was successfully inserted")
                return True
        except Exception as e:
            print(f"[INFO] Error saving bus arrival data: {e}")
        finally:
            self.close_connection()
        return False
class TrafficParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.model = None
        self.driver = None
        self.initialize_model()
        self.initialize_driver()
        
    def initialize_model(self):
        try:
            from tensorflow.keras.models import load_model
            self.model = load_model('/traffic/gfgModel.h5')
        except Exception as e:
            print(f"[INFO] Error loading traffic model: {e}")
            
    def initialize_driver(self):
        try:
            from selenium import webdriver
            from selenium.webdriver import FirefoxOptions
            opts = FirefoxOptions()
            opts.add_argument("--headless")
            self.driver = webdriver.Firefox(options=opts)
        except Exception as e:
            print(f"[INFO] Error initializing webdriver: {e}")
            
    def parse(self):
        try:
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
            return {
                'city': city,
                'traffic_point': traffic_point
            }
        except Exception as e:
            print(f"[INFO] Error parsing traffic: {e}")
            return None
            
    def save_to_db(self, data):
        if not data:
            return False
        try:
            if self.connect_to_db():
                query = 'INSERT INTO public."Traffic" VALUES (NOW(), %s, %s)'
                self.cursor.execute(query, (data['city'], data['traffic_point']))
                print("[INFO] Traffic data was successfully inserted")
                return True
        except Exception as e:
            print(f"[INFO] Error saving traffic data: {e}")
        finally:
            self.close_connection()
        return False
        
    def __del__(self):
        if self.driver:
            self.driver.quit()