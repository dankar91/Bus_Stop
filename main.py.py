from dataclasses import dataclass
import cv2
import numpy as np
from ByteTrack.tutorials.centertrack.byte_tracker import BYTETracker

class Args:
    def __init__(self):
        self.track_thresh = 0.25
        self.track_buffer = 30
        self.match_thresh = 0.8
        self.new_thresh = 0.25
        self.out_thresh = 0.1

args = Args()
from typing import Dict, List, Tuple
import time
import psycopg2
from datetime import datetime
@dataclass

class Detection:
    box: Tuple[int, int, int, int]  # xmin, ymin, xmax, ymax
    confidence: float
    class_id: int
    track_id: int = None

class DatabaseManager:
    def __init__(self, host='195.133.25.250', user='admin_user', password='strongpassword', database='postgres', port='5433'):
        self.connection_params = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'port': port
        }
        self.connection = None
        
    def connect(self):
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            self.connection.autocommit = True
            return True
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
            
    def save_statistics(self, stats: Dict):
        if not self.connection:
            self.connect()
            
        try:
            with self.connection.cursor() as cursor:
                # Сохраняем данные о пассажиропотоке
                passenger_query = """
                INSERT INTO public."Passenger_Traffic" 
                (datetime, bus_stop_id, number_of_passenger)
                VALUES (NOW(), %s, %s)
                """
                cursor.execute(passenger_query, (14, stats['people_count']))
                
                # Если обнаружен автобус, сохраняем информацию о его прибытии
                if stats['bus_count'] > 0:
                    bus_query = """
                    INSERT INTO public."Bus_Arrival"
                    (datetime, bus_stop_id, route_id, route_name, passenger_in)
                    VALUES (NOW(), %s, %s, %s, %s)
                    """
                    cursor.execute(bus_query, (14, 1, '14', stats['people_count']))
                
                # Сохраняем данные о времени ожидания
                waiting_query = """
                INSERT INTO public."Passenger_Waiting_Time"
                (datetime, bus_stop_id, passenger_id, waiting_time_seconds, route_id)
                VALUES (NOW(), %s, %s, %s, %s)
                """
                for passenger_id, waiting_time in enumerate(stats.get('waiting_times', []), 1):
                    cursor.execute(waiting_query, (14, passenger_id, waiting_time, 1))
                
        except Exception as e:
            print(f"[ERROR] Failed to save statistics: {e}")
class PassengerTracker:
    def __init__(self):
        self.tracker = BYTETracker(args, frame_rate=30)
        self.passenger_times = {}  # track_id -> start_time
        self.waiting_times = []
        
    def update(self, detections: List[Detection], frame_size: Tuple[int, int]) -> List[Detection]:
        detection_list = [
            {'bbox': [d.box[0], d.box[1], d.box[2], d.box[3]], 
             'score': d.confidence, 
             'class': d.class_id}
            for d in detections
        ]
        
        tracked_objects = self.tracker.step(detection_list)
        
        current_time = time.time()
        tracked_detections = []
        
        for track in tracked_objects:
            track_id = track['tracking_id']
            box = track['bbox']
            
            if track_id not in self.passenger_times:
                self.passenger_times[track_id] = current_time
                
            tracked_detections.append(Detection(
                box=tuple(box),
                confidence=track['score'],
                class_id=2,  # person
                track_id=track_id
            ))
            
        return tracked_detections
    
    def get_waiting_stats(self) -> Dict:
        current_time = time.time()
        current_waiting_times = [
            current_time - start_time
            for start_time in self.passenger_times.values()
        ]
        
        if not current_waiting_times:
            return {
                'avg_waiting_time': 0,
                'min_waiting_time': 0,
                'max_waiting_time': 0
            }
            
        return {
            'avg_waiting_time': np.mean(current_waiting_times),
            'min_waiting_time': np.min(current_waiting_times),
            'max_waiting_time': np.max(current_waiting_times)
        }
    
    def bus_arrived(self):
        """Вызывается при появлении автобуса"""
        current_time = time.time()
        for track_id, start_time in self.passenger_times.items():
            self.waiting_times.append(current_time - start_time)
        self.passenger_times.clear()

class VideoProcessor:
    def __init__(self, model, co_range_list: List[Dict]):
        self.model = model
        self.co_range_list = co_range_list
        self.tracker = PassengerTracker()
        self.frame_counter = 0
        
    def process_frame(self, frame) -> Tuple[np.ndarray, Dict]:
        self.frame_counter += 1
        detections = self._detect_objects(frame)
        tracked_detections = self.tracker.update(detections, frame.shape[:2])
        
        # Отрисовка и подготовка статистики
        frame = self._draw_detections(frame, tracked_detections)
        stats = self._prepare_statistics(tracked_detections)
        
        return frame, stats
    
    def _detect_objects(self, frame) -> List[Detection]:
        model_results = self.model(frame)[0]
        detections = []
        
        for data in model_results.boxes.data.tolist():
            confidence = data[4]
            if confidence < 0.2:
                continue
                
            box = tuple(map(int, data[:4]))
            class_id = int(data[5])
            
            if self._is_valid_detection(box, class_id):
                detections.append(Detection(box, confidence, class_id))
                
                if class_id == 0:  # bus
                    self.tracker.bus_arrived()
                    
        return detections
    
    def _is_valid_detection(self, box, class_id) -> bool:
        if class_id != 2:  # не человек
            return True
            
        xmin, ymin, xmax, ymax = box
        for co_range in self.co_range_list:
            if (xmax >= co_range['x_start'] and xmin <= co_range['x_end'] and
                ymax >= co_range['y_start'] and ymin <= co_range['y_end']):
                return False
        return True
    
    def _draw_detections(self, frame, detections: List[Detection]) -> np.ndarray:
        for detection in detections:
            color = (0, 255, 0) if detection.class_id == 0 else (255, 0, 0)
            x1, y1, x2, y2 = map(int, detection.box)
            cv2.rectangle(frame, 
                         (x1, y1),
                         (x2, y2),
                         color, 2)
            
            if detection.track_id is not None:
                waiting_time = time.time() - self.tracker.passenger_times.get(detection.track_id, time.time())
                cv2.putText(frame,
                           f"ID: {detection.track_id} Time: {int(waiting_time)}s",
                           (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.5,
                           color,
                           2)
        
        # Добавляем общую статистику
        stats = self.tracker.get_waiting_stats()
        cv2.putText(frame,
                   f"Avg waiting time: {int(stats['avg_waiting_time'])}s",
                   (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   1,
                   (0, 0, 255),
                   2)
        
        return frame
    
    def _prepare_statistics(self, detections: List[Detection]) -> Dict:
        people_count = sum(1 for d in detections if d.class_id == 2)
        bus_count = sum(1 for d in detections if d.class_id == 0)
        
        waiting_stats = self.tracker.get_waiting_stats()
        
        return {
            'people_count': people_count,
            'bus_count': bus_count,
            **waiting_stats
        }
class BusStopMonitor:
    def __init__(self, video_source, model, co_range_list, db_config):
        self.video_processor = VideoProcessor(model, co_range_list)
        self.db_manager = DatabaseManager(**db_config)
        self.video_source = video_source
        
    def run(self):
        print(f"Opening video source: {self.video_source}")
        cap = cv2.VideoCapture(self.video_source)
        
        if not cap.isOpened():
            print("Error: Could not open video source")
            return
            
        print("Video capture initialized successfully")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("End of video stream or error reading frame")
                    break
                    
                processed_frame, stats = self.video_processor.process_frame(frame)
                
                # Сохраняем статистику каждые N кадров
                if self.video_processor.frame_counter % 30 == 0:
                    self.db_manager.save_statistics(stats)
                
                # Показываем frame (в продакшене можно убрать)
                cv2.imshow('Bus Stop Monitor', processed_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            cap.release()
            cv2.destroyAllWindows()
# Пример использования:
if __name__ == "__main__":
    import os
    os.environ['DISPLAY'] = ':99'
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
    
    from xvfbwrapper import Xvfb
    vdisplay = Xvfb()
    vdisplay.start()
    '''from parsers.parser import WeatherParser, BusStopParser, TrafficParser
    from apscheduler.schedulers.background import BackgroundScheduler
    
    # Initialize parsers
    weather_parser = WeatherParser()
    bus_stop_parser = BusStopParser()
    traffic_parser = TrafficParser()
    
    # Set up scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: bus_stop_parser.parse() and bus_stop_parser.save_to_db(bus_stop_parser.parse()), 'interval', minutes=1)
    scheduler.add_job(lambda: traffic_parser.parse() and traffic_parser.save_to_db(traffic_parser.parse()), 'interval', hours=1)
    scheduler.add_job(lambda: weather_parser.parse() and weather_parser.save_to_db(weather_parser.parse()), 'interval', hours=3)
    scheduler.start()
    '''
    db_config = {
        'host': '195.133.25.250',
        'user': 'admin_user',
        'password': 'strongpassword',
        'database': 'postgres',
        'port': '5433'
    }
    
    # Инициализируем подключение к БД
    with psycopg2.connect(**db_config) as conn:
        print("Database connected successfully")
    
    print("Loading YOLO model...")
    from ultralytics import YOLO
    
    model = YOLO("models/best_l_last.pt")
    print("YOLO model loaded successfully")
    
    co_range_list = [
        {'x_start': 0, 'x_end': 100, 'y_start': 0, 'y_end': 100}
    ]
    print("Starting video monitoring...")
    
    monitor = BusStopMonitor(
        video_source='Samples/BusStop_Trim_3.mp4',  # или путь к видео файлу
        model=model,
        co_range_list=co_range_list,
        db_config=db_config
    )
    
    monitor.run()       