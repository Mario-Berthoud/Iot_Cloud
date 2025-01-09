FROM python:3.12-bullseye

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT [ "fastapi", "run", "main.py" ]
