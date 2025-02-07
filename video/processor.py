
import cv2
import numpy as np
from typing import List, Dict, Tuple
from trackers.passenger_tracker import Detection
from trackers.passenger_tracker import PassengerTracker
from database.manager import DatabaseManager
from config import bus_stop_id

class VideoProcessor:
    def __init__(self, model, co_range_list: List[Dict], db_manager: DatabaseManager, fps: int = 30):
        self.model = model
        self.co_range_list = co_range_list
        self.frame_counter = 0
        self.fps = fps
        self.tracker = PassengerTracker(fps=fps)
        self.db_manager = db_manager
        
    def process_frame(self, frame) -> Tuple[np.ndarray, Dict]:
        self.frame_counter += 1
        detections = self._detect_objects(frame)
        boxes = np.array([d.box for d in detections])
        scores = np.array([[d.confidence] for d in detections])
        class_ids = np.array([[d.class_id] for d in detections])
        
        output_results = np.concatenate([boxes, scores, class_ids], axis=1)
        tracked_detections = self.tracker.update(output_results, frame.shape[:2], self.db_manager)
        
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
                    
        return detections
    
    def _is_valid_detection(self, box, class_id) -> bool:
        if class_id != 2 or self.co_range_list is None:
            return True
            
        xmin, ymin, xmax, ymax = box
        for co_range in self.co_range_list:
            if (xmin >= co_range['x_start'] and xmax <= co_range['x_end'] and
                ymin >= co_range['y_start'] and ymax <= co_range['y_end']):
                return True
        return False
    
    def _draw_detections(self, frame, detections: List[Detection]) -> np.ndarray:
        if self.co_range_list:
            for co_range in self.co_range_list:
                cv2.rectangle(frame,
                            (co_range['x_start'], co_range['y_start']),
                            (co_range['x_end'], co_range['y_end']),
                            (0, 0, 255),
                            2)
            
        stats = self.tracker.get_waiting_stats()
        cv2.putText(frame,
                   f"Avg wait: {int(stats['avg_waiting_time'])}s",
                   (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   1,
                   (0, 255, 0),
                   2)
        cv2.putText(frame,
                   f"Max: {int(stats['max_waiting_time'])}s",
                   (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   1,
                   (0, 255, 0),
                   2)
        
        for detection in detections:
            if detection.class_id == 2:  # только для людей
                is_inside_frame = True
                if self.co_range_list is not None:
                    xmin, ymin, xmax, ymax = detection.box
                    is_inside_frame = False
                    for co_range in self.co_range_list:
                        if (xmin >= co_range['x_start'] and xmax <= co_range['x_end'] and
                            ymin >= co_range['y_start'] and ymax <= co_range['y_end']):
                            is_inside_frame = True
                            break

                if is_inside_frame:
                    x1, y1, x2, y2 = map(int, detection.box)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    
                    if detection.track_id is not None and detection.track_id in self.tracker.passenger_frames:
                        passenger_data = self.tracker.passenger_frames[detection.track_id]
                        start_frame = passenger_data['start_frame']
                        waiting_time = (self.frame_counter - start_frame) / self.fps
                        cv2.putText(frame,
                                  f"ID: {detection.track_id} Time: {int(waiting_time)}s",
                                  (x1, y1-10),
                                  cv2.FONT_HERSHEY_SIMPLEX,
                                  0.5,
                                  (255, 0, 0),
                                  2)
            elif detection.class_id == 0:  # для автобусов
                x1, y1, x2, y2 = map(int, detection.box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        return frame
    
    def _prepare_statistics(self, detections: List[Detection]) -> Dict:
        people_count = 0
        bus_count = 0
        passenger_stats = []
        
        print("\n=== Frame Statistics ===")
        print(f"Current frame: {self.frame_counter}")
        
        for d in detections:
            if d.class_id == 0:
                bus_count += 1
                print(f"Bus detected!")
            elif d.class_id == 2:
                is_inside_frame = True
                if self.co_range_list is not None:
                    xmin, ymin, xmax, ymax = d.box
                    is_inside_frame = False
                    for co_range in self.co_range_list:
                        if (xmin >= co_range['x_start'] and xmax <= co_range['x_end'] and
                            ymin >= co_range['y_start'] and ymax <= co_range['y_end']):
                            is_inside_frame = True
                            break
                
                if is_inside_frame:
                    people_count += 1
                    passenger_data = self.tracker.passenger_frames.get(d.track_id)
                    
                    if not passenger_data:
                        original_frame = None
                        for pid, pdata in self.tracker.passenger_frames.items():
                            if pid == d.track_id:
                                original_frame = pdata['start_frame']
                                break
                        
                        start_frame = original_frame if original_frame else self.frame_counter
                        
                        self.tracker.passenger_frames[d.track_id] = {
                            'start_frame': start_frame,
                            'last_seen': self.frame_counter,
                            'is_tracked': True,
                            'first_seen': True
                        }
                        
                        try:
                            self.db_manager.save_passenger_appearance(d.track_id, bus_stop_id)
                            if not original_frame:
                                print(f"[NEW] Passenger ID {d.track_id} first detected at frame {start_frame}")
                            passenger_stats.append({
                                'id': d.track_id,
                                'start_frame': start_frame,
                                'last_frame': self.frame_counter
                            })
                        except Exception as e:
                            print(f"[ERROR] Failed saving passenger {d.track_id}: {e}")
                    else:
                        passenger_data['last_seen'] = self.frame_counter
                        
                        if not passenger_data['is_tracked']:
                            passenger_data['is_tracked'] = True
                            try:
                                self.db_manager.save_passenger_appearance(d.track_id, bus_stop_id)
                                print(f"[RETURN] Passenger ID {d.track_id} returned at frame {self.frame_counter}")
                            except Exception as e:
                                print(f"[ERROR] Failed re-registering passenger {d.track_id}: {e}")
                        
                        passenger_stats.append({
                            'id': d.track_id,
                            'start_frame': passenger_data['start_frame'],
                            'last_frame': self.frame_counter
                        })

        
        for track_id, passenger_data in list(self.tracker.passenger_frames.items()):
            if passenger_data['is_tracked']:
                frames_not_seen = self.frame_counter - passenger_data['last_seen']
                if frames_not_seen > self.fps * 3:
                    waiting_time = int((passenger_data['last_seen'] - passenger_data['start_frame']) / self.fps)
                    try:
                        self.db_manager.update_passenger_departure(track_id, waiting_time)
                        print(f"Passenger {track_id} left after {waiting_time} seconds")
                        passenger_data['is_tracked'] = False
                    except Exception as e:
                        print(f"Error updating departure for passenger {track_id}: {e}")

        waiting_stats = self.tracker.get_waiting_stats()
        
        print("\n=== Current Passengers ===")
        for stat in passenger_stats:
            print(f"Passenger ID: {stat['id']} - First seen: frame {stat['start_frame']}, Last seen: frame {stat['last_frame']}")
        print(f"Total passengers: {people_count}")
        print("=====================\n")
        
        return {
            'people_count': people_count,
            'bus_count': bus_count,
            'passenger_stats': passenger_stats,
            **waiting_stats
        }
