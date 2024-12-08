from apscheduler.schedulers.blocking import BlockingScheduler
from parsers.bus_stop.bus_stop_parser import bus_arrival
from parsers.traffic.traffic_parser import traffic
from parsers.weather.weather_parser import weather

scheduler_bus = BlockingScheduler()
scheduler_bus.add_job(bus_arrival, 'interval', minutes=1)
scheduler_bus.start()

scheduler_traffic = BlockingScheduler()
scheduler_traffic.add_job(traffic, 'interval', hours=1)
scheduler_traffic.start()


scheduler_weather = BlockingScheduler()
scheduler_weather.add_job(weather, 'interval', hours=3)
scheduler_weather.start()
