FROM python:3.12-slim

WORKDIR /opt/plz-map/server
COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ ./

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec gunicorn --bind 0.0.0.0:8000 app.application:application"]
