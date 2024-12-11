from dataclasses import dataclass
import cv2
import numpy as np
from bytetrack.byte_tracker import BYTETracker
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
    def __init__(self, host, user, password, db_name, port='5434'):
        self.connection_params = {
            'host': host,
            'user': user,
            'password': password,
            'database': db_name,
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
                query = """
                INSERT INTO public."BusStop_Stats" 
                (timestamp, people_count, bus_count, avg_waiting_time, 
                 min_waiting_time, max_waiting_time) 
                VALUES (NOW(), %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    stats['people_count'],
                    stats['bus_count'],
                    stats['avg_waiting_time'],
                    stats['min_waiting_time'],
                    stats['max_waiting_time']
                ))
        except Exception as e:
            print(f"[ERROR] Failed to save statistics: {e}")
class PassengerTracker:
    def __init__(self):
        self.tracker = BYTETracker(
            track_thresh=0.25,
            track_buffer=30,
            match_thresh=0.8,
            frame_rate=30
        )
        self.passenger_times = {}  # track_id -> start_time
        self.waiting_times = []
        
    def update(self, detections: List[Detection], frame_size: Tuple[int, int]) -> List[Detection]:
        detection_array = np.array([
            [d.box[0], d.box[1], d.box[2], d.box[3], d.confidence, d.class_id]
            for d in detections
        ])
        
        tracked_objects = self.tracker.update(
            detection_array,
            [frame_size[0], frame_size[1]],
            [frame_size[0], frame_size[1]]
        )
        
        current_time = time.time()
        tracked_detections = []
        
        for track in tracked_objects:
            track_id = track.track_id
            box = track.tlbr.astype(int)
            
            if track_id not in self.passenger_times:
                self.passenger_times[track_id] = current_time
                
            tracked_detections.append(Detection(
                box=tuple(box),
                confidence=track.score,
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
            cv2.rectangle(frame, 
                         (detection.box[0], detection.box[1]),
                         (detection.box[2], detection.box[3]),
                         color, 2)
            
            if detection.track_id is not None:
                waiting_time = time.time() - self.tracker.passenger_times.get(detection.track_id, time.time())
                cv2.putText(frame,
                           f"ID: {detection.track_id} Time: {int(waiting_time)}s",
                           (detection.box[0], detection.box[1]-10),
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
        cap = cv2.VideoCapture(self.video_source)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
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
    db_config = {
        'host': 'localhost',
        'user': 'your_user',
        'password': 'your_password',
        'db_name': 'your_db'
    }
    
    # Создаем SQL таблицу если еще не создана
    create_table_query = """
    CREATE TABLE IF NOT EXISTS public."BusStop_Stats" (
        timestamp TIMESTAMP NOT NULL,
        people_count INTEGER NOT NULL,
        bus_count INTEGER NOT NULL,
        avg_waiting_time FLOAT NOT NULL,
        min_waiting_time FLOAT NOT NULL,
        max_waiting_time FLOAT NOT NULL
    );
    """
    
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(create_table_query)
    
    monitor = BusStopMonitor(
        video_source=0,  # или путь к видео файлу
        model=your_yolo_model,
        co_range_list=your_co_range_list,
        db_config=db_config
    )
    
    monitor.run()       