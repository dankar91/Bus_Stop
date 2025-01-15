
import cv2
from video.processor import VideoProcessor
from database.manager import DatabaseManager

class BusStopMonitor:
    def __init__(self, video_source, model, co_range_list, db_config, show_display=False, output_path=None):
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            raise ValueError(f"Error opening video source: {video_source}")
        self.fps = int(cap.get(cv2.CAP_PROP_FPS))
        cap.release()
        
        self.db_manager = DatabaseManager()
        self.video_processor = VideoProcessor(model, co_range_list, self.db_manager, self.fps)
        self.video_source = video_source
        self.show_display = show_display
        self.output_path = output_path
        
    def run(self):
        print(f"Opening video source: {self.video_source}")
        cap = cv2.VideoCapture(self.video_source)
        
        if not cap.isOpened():
            print("Error: Could not open video source")
            return
            
        print("Video capture initialized successfully")
        
        video_writer = None
        if self.output_path:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            video_writer = cv2.VideoWriter(
                self.output_path,
                cv2.VideoWriter_fourcc(*'mp4v'),
                fps,
                (width, height)
            )
            print(f"Saving output video to: {self.output_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("End of video stream or error reading frame")
                    break
                    
                processed_frame, stats = self.video_processor.process_frame(frame)
                print(f"Processing frame {self.video_processor.frame_counter}/{total_frames}")
                
                if self.video_processor.frame_counter % 100 == 0:
                    self.db_manager.save_passenger_count(stats)
                
                if self.video_processor.frame_counter % (self.fps * 5) == 0:
                    self.db_manager.save_waiting_time(stats)
                
                if video_writer:
                    video_writer.write(processed_frame)
                
                if self.show_display:
                    cv2.imshow('Bus Stop Monitor', processed_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    
        finally:
            cap.release()
            if video_writer:
                video_writer.release()
            cv2.destroyAllWindows()
