
import psycopg2

def create_database():
    db_config = {
        'host': '195.133.25.250',
        'user': 'admin_user',
        'password': 'strongpassword',
        'database': 'postgres',
        'port': '5433'
    }

    create_table_query = """
    CREATE TABLE IF NOT EXISTS public."Routes" (
        route_id SERIAL PRIMARY KEY,
        route_name VARCHAR(50) NOT NULL,
        first_bus_stop_id INTEGER NOT NULL,
        final_bus_stop_id INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public."Bus_stops" (
        bus_stop_id SERIAL PRIMARY KEY,
        bus_stop_name VARCHAR(100) NOT NULL,
        bus_stop_address VARCHAR(200) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public."Bus_stop_Route" (
        bus_stop_route_id SERIAL PRIMARY KEY,
        bus_stop_id INTEGER REFERENCES public."Bus_stops"(bus_stop_id),
        route_id INTEGER REFERENCES public."Routes"(route_id)
    );

    CREATE TABLE IF NOT EXISTS public."Bus_Arrival" (
        datetime TIMESTAMP NOT NULL,
        bus_stop_id INTEGER REFERENCES public."Bus_stops"(bus_stop_id),
        route_id INTEGER REFERENCES public."Routes"(route_id),
        route_name VARCHAR(50) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public."Passenger_Traffic" (
        datetime TIMESTAMP NOT NULL,
        bus_stop_id INTEGER REFERENCES public."Bus_stops"(bus_stop_id),
        number_of_passenger INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public."Weather" (
        datetime TIMESTAMP NOT NULL,
        temperature INTEGER NOT NULL,
        condition VARCHAR(50) NOT NULL,
        city VARCHAR(50) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public."Traffic" (
        datetime TIMESTAMP NOT NULL,
        traffic INTEGER NOT NULL,
        city VARCHAR(50) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public."Passenger_Waiting_Time" (
        datetime TIMESTAMP NOT NULL,
        bus_stop_id INTEGER REFERENCES public."Bus_stops"(bus_stop_id),
        passenger_id INTEGER NOT NULL,
        waiting_time_seconds INTEGER NOT NULL,
        route_id INTEGER REFERENCES public."Routes"(route_id)
    );
    """

    try:
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_table_query)
                print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    create_database()
