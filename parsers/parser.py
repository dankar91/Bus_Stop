from abc import ABC, abstractmethod
import psycopg2
from bs4 import BeautifulSoup
import requests
from config import host, user, password, database, port, bus_stop_id, Weather_API_key


class BaseParser(ABC):
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def connect_to_db(self):
        try:
            self.connection = psycopg2.connect(
                host = host,
                user = user,
                password = password,
                database = database,
                port = port
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
        self.url = f'https://api.weatherxu.com/v1/weather?api_key={Weather_API_key}'
        self.weather_conditions = {
    "clear": "ясно",
    "partly_cloudy": "переменная облачность",
    "mostly_cloudy": "преимущественно облачно",
    "cloudy": "облачно",
    "light_rain": "небольшой дождь",
    "rain": "дождь",
    "heavy_rain": "сильный дождь",
    "freezing_rain": "ледяной дождь",
    "thunderstorm": "гроза",
    "thunder_rain": "дождь с грозой",
    "light_snow": "небольшой снег",
    "snow": "снег",
    "heavy_snow": "сильный снег",
    "sleet": "дождь с морозом, ледяной дождь",
    "hail": "град",
    "windy": "ветрено",
    "fog": "туман",
    "mist": "дымка",
    "haze": "лёгкая дымка",
    "smoke": "дым",
    "dust": "пыль",
    "tornado": "торнадо",
    "tropical_storm": "тропический шторм",
    "hurricane": "ураган",
    "sandstorm": "песчаная буря",
    "blizzard": "метель"
}
    def parse(self):
        try:
            lat = 55.0415
            lon = 82.9346
            url_full = f'{self.url}&lat={lat}&lon={lon}'
            json_data = requests.get(url_full).json()
            formatted_data = json_data['data']['currently']
            temperature = int(formatted_data['temperature'])
            condition = weather_conditions.get(formatted_data['icon'])
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
                    'bus_stop_id': bus_stop_id,
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
            import tensorflow as tf
            from tensorflow.keras.preprocessing import image
            tf.keras.losses.Reduction.AUTO = tf.keras.losses.Reduction.SUM
            from tensorflow.keras.models import load_model
            self.model = load_model('/parsers/traffic/gfgModel.keras', compile=False)
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
            # Загружаем страницу
            self.driver.get("https://yandex.ru/maps/65/novosibirsk/probki/?ll=82.920430%2C55.030199&source=traffic&z=12")
            sleep(5)

            # Делаем скриншот
            screenshot_path = '/parsers/traffic/screenie.png'
            if not self.driver.save_screenshot(screenshot_path):
                raise ValueError("[INFO] Screenshot not saved successfully")

            # Загружаем скриншот с помощью OpenCV
            img = cv2.imread(screenshot_path)
            if img is None:
                raise ValueError("[INFO] Failed to read screenshot with OpenCV")

            # Обрезаем изображение
            crop_img = img[120:170, 0:200]
            crop_path = '/parsers/traffic/croped_scr.png'
            cv2.imwrite(crop_path, crop_img)

            # Загружаем обрезанное изображение
            img_height, img_width = 150, 150
            img = image.load_img(crop_path, target_size=(img_height, img_width))
            if img is None:
                raise ValueError("[INFO] Failed to load cropped image")

            # Используем ожидаемый размер входного изображения
            img = image.load_img(crop_path, target_size=(180, 180))
            img_array = image.img_to_array(img)
            img_array = tf.expand_dims(img_array, 0) 

            # Предсказание модели
            predictions = self.model.predict(img_array)
            if predictions is None or len(predictions) == 0:
                raise ValueError("[INFO] Model returned no predictions")

            # Обработка предсказаний
            class_names = ['0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9']
            score = tf.nn.softmax(predictions[0])
            traffic_point = class_names[np.argmax(score)]
            city = 'Новосибирск'


            print(
                f"This image most likely belongs to {traffic_point} with a "
                f"{100 * np.max(score):.2f}% confidence."
            )
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
                self.cursor.execute(query, (data['traffic_point'], (data['city'])))
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