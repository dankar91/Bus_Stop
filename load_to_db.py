from yolo_detection import process_video
import psycopg2
# from sshtunnel import SSHTunnelForwarder
from config import host, user, password, db_name

try:

    params = {
        # 'dbname': db_name,
        'user': user,
        'password': password,
        'host': 'localhost',
        'port': 5434
        }

    conn = psycopg2.connect(**params)
    # curs = conn.cursor()
    print("database connected")

    # path = 'benchmark/result.mp4'
    # path = 'http://195.88.112.26:555/PPkRG44m?container=mjpeg&stream=main'
    path = 'video-2777072-0213-1255-5.flv'
    process_video(path, counter=0, db_conn=conn)    
except:
    print("Connection Failed")