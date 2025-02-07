
import numpy as np
from typing import Dict, List, Tuple
from ByteTrack.yolox.tracker.byte_tracker import BYTETracker
import time
from config import bus_stop_id

class Detection:
    def __init__(self, box, confidence, class_id, track_id=None):
        self.box = box  # xmin, ymin, xmax, ymax
        self.confidence = confidence
        self.class_id = class_id
        self.track_id = track_id

class Args:
    def __init__(self):
        self.track_thresh = 0.35
        self.track_buffer = 40
        self.match_thresh = 0.8
        self.new_thresh = 0.25
        self.out_thresh = 0.1
        self.mot20 = False

class PassengerTracker:
    def __init__(self, fps=None):
        self.fps = fps if fps is not None else 30  # Значение по умолчанию если не передано
        self.tracker = BYTETracker(Args(), frame_rate=self.fps)
        self.passenger_frames = {}  # track_id -> dict with tracking data
        self.current_frame = 0
        
    def update(self, detections: np.ndarray, frame_size: Tuple[int, int], db_manager) -> List[Detection]:
        self.current_frame += 1
        
        if len(detections) > 0:
            scores = detections[:, 4]
            class_ids = detections[:, 5]
            bboxes = detections[:, :4]  # x1y1x2y2
        else:
            scores = np.array([])
            class_ids = np.array([])
            bboxes = np.array([])

        remain_inds = scores > self.tracker.args.track_thresh
        dets = bboxes[remain_inds]
        scores_keep = scores[remain_inds]
        
        tracked_objects = self.tracker.update(np.concatenate([dets, scores_keep[:, None]], axis=1), [frame_size[0], frame_size[1]], frame_size)
        
        current_time = time.time()
        tracked_detections = []
        
        for track in tracked_objects:
            track_id = track.track_id
            box = track.tlbr
            
            if track_id not in self.passenger_frames:
                # Если видим пассажира в первый раз
                self.passenger_frames[track_id] = {
                    'start_frame': self.current_frame,
                    'last_seen': self.current_frame,
                    'is_tracked': True
                }
                print(f"[NEW] Passenger ID {track_id} first detected at frame {self.current_frame}")
                # Сохраняем нового пассажира в базу данных
                try:
                    db_manager.save_passenger_appearance(track_id, bus_stop_id)
                except Exception as e:
                    print(f"Failed to save passenger {track_id}: {e}")
            else:
                # Обновляем только столбец last_seen для каждого пассажира
                self.passenger_frames[track_id]['last_seen'] = self.current_frame
                
            tracked_detections.append(Detection(
                box=tuple(box),
                confidence=track.score,
                class_id=2,  # person
                track_id=track_id
            ))
        return tracked_detections
    
    def get_waiting_stats(self) -> Dict:
        current_waiting_times = []
        min_waiting_threshold = 5  # минимальное время ожидания в секундах

        for track_id, data in self.passenger_frames.items():
            if data['is_tracked']:
                waiting_time = (self.current_frame - data['start_frame']) / self.fps
                if waiting_time >= min_waiting_threshold:
                    current_waiting_times.append(waiting_time)

        if not current_waiting_times:
            return {
                'avg_waiting_time': 0,
                'min_waiting_time': 0,
                'max_waiting_time': 0,
                'current_waiting_times': []
            }

        return {
            'avg_waiting_time': np.mean(current_waiting_times),
            'min_waiting_time': np.min(current_waiting_times),
            'max_waiting_time': np.max(current_waiting_times),
            'current_waiting_times': current_waiting_times
        }
