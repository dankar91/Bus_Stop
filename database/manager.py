
import psycopg2
from typing import Dict
from config import host, user, password, database, port, bus_stop_id

class DatabaseManager:
    def __init__(self):
        self.connection_params = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'port': port
        }
        self.connection = None
        self.connect()
        
    def connect(self):
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            self.connection.autocommit = True
            return True
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
            
    def save_passenger_count(self, stats: Dict):
        try:
            if not self.connection or self.connection.closed:
                self.connect()
                
            with self.connection.cursor() as cursor:
                passenger_query = """
                INSERT INTO public."Passenger_Traffic" 
                (datetime, bus_stop_id, number_of_passenger)
                VALUES (NOW(), %s, %s)
                """
                cursor.execute(passenger_query, (bus_stop_id, stats['people_count']))
                self.connection.commit()
                
        except Exception as e:
            print(f"[ERROR] Failed to save passenger statistics: {e}")
            if self.connection:
                self.connection.rollback()
                self.connection.close()
                self.connection = None
                
    def save_waiting_time(self, stats: Dict):
        try:
            if not self.connection or self.connection.closed:
                self.connect()
                
            with self.connection.cursor() as cursor:
                waiting_query = """
                INSERT INTO public."Passenger_Waiting_Time"
                (datetime, bus_stop_id, average_waiting_time, max_waiting_time)
                VALUES (NOW(), %s, %s, %s)
                """
                avg_time = stats.get('avg_waiting_time', 0)
                max_time = stats.get('max_waiting_time', 0)
                cursor.execute(waiting_query, (bus_stop_id, int(avg_time), int(max_time)))
                self.connection.commit()
                
        except Exception as e:
            print(f"[ERROR] Failed to save statistics: {e}")
            if self.connection:
                self.connection.rollback()
                self.connection.close()
                self.connection = None
            if not self.connection or self.connection.closed:
                self.connect()
                
            with self.connection.cursor() as cursor:
                waiting_query = """
                INSERT INTO public."Passenger_Waiting_Time"
                (datetime, bus_stop_id, average_waiting_time, max_waiting_time)
                VALUES (NOW(), %s, %s, %s)
                """
                avg_time = stats.get('avg_waiting_time', 0)
                max_time = stats.get('max_waiting_time', 0)
                cursor.execute(waiting_query, (bus_stop_id, int(avg_time), int(max_time)))
                self.connection.commit()
                
        except Exception as e:
            print(f"[ERROR] Failed to save statistics: {e}")
            if self.connection:
                self.connection.rollback()
                self.connection.close()
                self.connection = None

    def save_passenger_appearance(self, track_id: int, bus_stop_id: int):
        try:
            if not self.connection or self.connection.closed:
                self.connect()

            with self.connection.cursor() as cursor:
                query = """
                    INSERT INTO public."Passengers" (passenger_id, bus_stop_id, appearance_time)
                    VALUES (%s, %s, NOW())
                """
                cursor.execute(query, (track_id, bus_stop_id))
                self.connection.commit()
        except Exception as e:
            print(f"[ERROR] Failed to save passenger appearance: {e}")
            if self.connection:
                self.connection.rollback()

    def update_passenger_departure(self, track_id: int, waiting_time: int):
        try:
            if not self.connection or self.connection.closed:
                self.connect()

            with self.connection.cursor() as cursor:
                query = """
                    UPDATE public."Passengers"
                    SET departure_time = NOW(),
                        waiting_time = %s
                    WHERE passenger_id = %s AND departure_time IS NULL
                """
                cursor.execute(query, (waiting_time, track_id))
                self.connection.commit()
        except Exception as e:
            print(f"[ERROR] Failed to update passenger departure: {e}")
            if self.connection:
                self.connection.rollback()
