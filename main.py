
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['DISPLAY'] = ':99'

from ultralytics import YOLO
from video.monitor import BusStopMonitor
from config import host, user, password, database, port
import psycopg2
from parsers.parser import WeatherParser, BusStopParser, TrafficParser
from apscheduler.schedulers.background import BackgroundScheduler

if __name__ == "__main__":
    # Инициализируем парсеры
    weather_parser = WeatherParser()
    bus_stop_parser = BusStopParser()
    traffic_parser = TrafficParser()

       
    # Настроим расписание парсеров
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: bus_stop_parser.parse() and bus_stop_parser.save_to_db(bus_stop_parser.parse()), 'interval', minutes=1)
    scheduler.add_job(lambda: traffic_parser.parse() and traffic_parser.save_to_db(traffic_parser.parse()), 'interval', hours=1)
    scheduler.add_job(lambda: weather_parser.parse() and weather_parser.save_to_db(weather_parser.parse()), 'interval', hours=3)
    scheduler.start()
    
    # Загрузим данные для подключения к базе данных
    db_config = {
        'host': host,
        'user': user,
        'password': password,
        'database': database,
        'port': port
    }
    
    # Инициализируем подключение к базе данных
    with psycopg2.connect(**db_config) as conn:
        print("Database connected successfully")
    
    # Запустим парсеры
    weather_parser.parse()
    weather_parser.save_to_db(weather_parser.parse())

    bus_stop_parser.parse()
    bus_stop_parser.save_to_db(bus_stop_parser.parse())

    traffic_parser.parse() 
    traffic_parser.save_to_db(traffic_parser.parse())

    # Обозначим параметры
    print("Loading YOLO model...")
    model = YOLO("yolov8x.pt")
    model.track = True
    model.task = 'detect'
    model.tracker = "bytetrack"
    print("YOLO model loaded successfully")
    co_range_list = [{'x_start': 800, 'x_end': 3000, 'y_start': 500, 'y_end': 2000}]
    
 
    # Запускаем сервис   
    print("Starting video monitoring...")
    monitor = BusStopMonitor(
        video_source='samples/BusStop_Trim_3.mp4',
        model=model,
        co_range_list=co_range_list,
        db_config=db_config,
        show_display=False,
        output_path='output.mp4'
    )
    
    monitor.run()
