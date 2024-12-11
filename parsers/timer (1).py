from apscheduler.schedulers.blocking import BlockingScheduler
from parsers import WeatherParser, BusStopParser, TrafficParser

def run_weather_parser():
    parser = WeatherParser()
    data = parser.parse()
    parser.save_to_db(data)
def run_bus_stop_parser():
    parser = BusStopParser()
    data = parser.parse()
    parser.save_to_db(data)
def run_traffic_parser():
    parser = TrafficParser()
    data = parser.parse()
    parser.save_to_db(data)

scheduler = BlockingScheduler()
scheduler.add_job(run_bus_stop_parser, 'interval', minutes=1)
scheduler.add_job(run_traffic_parser, 'interval', hours=1)
scheduler.add_job(run_weather_parser, 'interval', hours=3)
scheduler.start()