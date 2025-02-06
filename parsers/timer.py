from parser import WeatherParser, BusStopParser, TrafficParser
from apscheduler.schedulers.background import BackgroundScheduler

# Инициализируем парсеры
weather_parser = WeatherParser()
bus_stop_parser = BusStopParser()
traffic_parser = TrafficParser()

weather_parser.parse()
weather_parser.save_to_db(weather_parser.parse())

bus_stop_parser.parse()
bus_stop_parser.save_to_db(bus_stop_parser.parse())

traffic_parser.parse() 
traffic_parser.save_to_db(traffic_parser.parse())

# Настроим расписание
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: bus_stop_parser.parse() and bus_stop_parser.save_to_db(bus_stop_parser.parse()), 'interval', minutes=1)
scheduler.add_job(lambda: traffic_parser.parse() and traffic_parser.save_to_db(traffic_parser.parse()), 'interval', hours=1)
scheduler.add_job(lambda: weather_parser.parse() and weather_parser.save_to_db(weather_parser.parse()), 'interval', hours=3)
scheduler.start()