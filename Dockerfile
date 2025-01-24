FROM python:3.10

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean

WORKDIR /docker
COPY ./main.py /docker/
COPY ./requirements.txt /docker/
COPY ./ByteTrack/ /docker/ByteTrack/
COPY ./database/ /docker/database/
COPY ./models/best_l_last.pt /docker/models/
COPY ./parsers/parser.py /docker/parsers/
COPY ./parsers/traffic/gfgModel.keras /docker/parsers/traffic/
COPY ./trackers/ /docker/trackers/
COPY ./video/ /docker/video/
RUN pip install --no-cache-dir -r requirements.txt
CMD [ "python", "./main.py" ]