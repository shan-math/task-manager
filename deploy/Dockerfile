FROM python:3.11-slim

WORKDIR /app

COPY Backend/requirements.txt ./Backend/requirements.txt
RUN pip install --no-cache-dir -r Backend/requirements.txt

COPY Backend/ ./Backend/
COPY Frontend/ ./Frontend/

WORKDIR /app/Backend
RUN mkdir -p uploads

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
EXPOSE 5000

CMD ["python", "app.py"]
