import cv2
from ultralytics import YOLO
import time
def yoloDetection(frame, model, abs_co_range_list):
    
    # Цвета
    GREEN = (0, 255, 0)
    BLUE = (255, 0, 0)
    RED = (0, 0, 255)

    # Производим анализ кадра 
    detections = model(frame)[0]
    people_detected = 0
    bus_detected = 0
    # Перебираем все найденные объекты
    for data in detections.boxes.data.tolist():
        # Получаем надежность
        confidence = data[4]
        # Пропускаем объекты с низкой надежностью
        CONFIDENCE_THRESHOLD = 0.2
        if float(confidence) < CONFIDENCE_THRESHOLD:
            continue
        # Проверка на попадание в отсечение
        xmin, ymin, xmax, ymax = int(data[0]), int(data[1]), int(data[2]), int(data[3])
        isValid = True
        for co_range in abs_co_range_list:
            if data[5] == 2:
                if xmax >= co_range['x_start'] and xmin <= co_range['x_end']:
                    if ymax >= co_range['y_start'] and ymin <= co_range['y_end']:
                        isValid = False
        
        if isValid:
            # Рисуем рамку        
            if data[5] == 0:
                color = GREEN
                bus_detected += 1
            elif data[5] == 2:
                color = BLUE
                people_detected += 1
            else:
                color = RED
            frame = cv2.rectangle(frame, (xmin, ymin) , (xmax, ymax), color, 2)
    
    print(f'People: {people_detected}, Bus: {bus_detected}')
    data = {
        'people': people_detected,
        'bus': bus_detected,
    }
    return frame, data

def get_absolute_coord(frame, x_percent_range, y_percent_range):
    # Считываем размерность изображения
    height, width = frame.shape[:2]
    # Вычисляем область показа в пикселях
    return dict(
        y_start = int(height*y_percent_range[0]/100),
        y_end = int(height*y_percent_range[1]/100),
        x_start = int(width*x_percent_range[0]/100),
        x_end = int(width*x_percent_range[1]/100)
    )

def get_crop(frame, x_percent_range, y_percent_range):
    """Получения кропа изображения по диапазону в процентах"""
    abs_coord = get_absolute_coord(frame, x_percent_range, y_percent_range)
    return frame[abs_coord['y_start']:abs_coord['y_end'],
                 abs_coord['x_start']:abs_coord['x_end']]

def vis_rectangle_by_percent(frame, x_percent_range, y_percent_range):
    """Рисование квадратной рамки по процентам"""
    abs_coord = get_absolute_coord(frame, x_percent_range, y_percent_range)
    return cv2.rectangle(frame, (abs_coord['x_start'], abs_coord['y_start']) ,
                         (abs_coord['x_end'], abs_coord['y_end']), (0, 100, 255), 2)

def process_video(path, counter, db_conn):
    if db_conn != None:
        # Курсор
        cur = db_conn.cursor()
    
    video_path = path
    # file_name = r'таймлапс2'
    # video_path = rf'{file_name}.mp4'
    # Модель для YOLO
    # model = YOLO('yolov8x-p2.yaml').load('trained_models/best_x_ver3.pt')
    model = YOLO("models/best_yolov8x")
    # model = YOLO("yolov8n.pt")

    # Счтитываем параметры видео
    vid = cv2.VideoCapture(video_path)
    # vid.set(cv2.CAP_PROP_BUFFERSIZE, 60)
    video_height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_framerate = vid.get(cv2.CAP_PROP_FPS)

    # show_frame_x_percent =(0, 50)
    # show_frame_y_percent = (45, 100)

    # show_frame_x_percent =(20, 90)
    # show_frame_y_percent = (25, 85)

    show_frame_x_percent =(0, 50)
    show_frame_y_percent = (0, 70)

    # Границы отсечения в обрезанном кадре в процентах
    co_range_list = list()
    co_range_list.append(
        dict(
            xmin = 0,
            xmax = 100,
            ymin = 0,
            ymax = 12
        )
    )
    co_range_list.append(
        dict(
            xmin = 0,
            xmax = 45,
            ymin = 0,
            ymax = 100
        )
    )
    co_range_list.append(
        dict(
            xmin = 0,
            xmax = 65,
            ymin = 0,
            ymax = 30
        )
    )
    abs_co_range_list = list()

    INF = 999999
    # Сколько времени видео обработать в секундах
    TIME_COUNT = 100
    # Частота кадров в секунду для сохранения
    OUTPUT_FPS = 0.1
    # Счетчики считанных и сохраненных кадров
    frameNr = 0
    savedFrameNr = 0
    # Далле считываем каждый framePerShot кадр
    framePerShot = video_framerate / OUTPUT_FPS

    prev = 0

    while (True):        
        # Читаем кадр, если успешно, то работаем
        success, frame = vid.read()
        
        if success and (frameNr % int(framePerShot) == 0):
            # Проверяем нужен ли нам кадр
            while True:
                time_elapsed = time.time() - prev
                if time_elapsed > 1./OUTPUT_FPS:
                    break                   
            prev = time.time()
            time_to_bd = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(prev))
            # Применяем кроп
            frame = get_crop(frame, show_frame_x_percent, show_frame_y_percent)
            # Высчитываем абсолютные координаты отсечения
            if abs_co_range_list == list():
                for co_range in co_range_list:
                    abs_co_range_list.append(get_absolute_coord(frame,
                                                                (co_range['xmin'], co_range['xmax']),
                                                                (co_range['ymin'], co_range['ymax'])
                                                                )
                                            )
            # Распознаем и рисуем рамки
            frame, data = yoloDetection(frame, model, abs_co_range_list)
            if db_conn:
                query = 'INSERT INTO public."Passenger_traffic" VALUES (%s, %s, %s)'
                #query_data = (time_to_bd, 14, data['people'])
                query_data = (time_to_bd, 14, data['people'].rolling(window=10).mean().reset_index(level=0, drop=True))


                # добавляем строку в таблицу people
                cur.execute(query, query_data)
                # выполняем транзакцию
                db_conn.commit()  
            
            delay = int(1000/OUTPUT_FPS)
           
            # Увеличиваем номер кадра
            savedFrameNr += 1

                            
            
        elif not success:
            cv2.destroyAllWindows()
            break
        frameNr += 1

path = 'таймлапс2.mp4'
process_video(path, counter=0, db_conn=None)