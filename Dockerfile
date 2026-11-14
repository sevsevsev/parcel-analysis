FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends gdal-bin libgdal-dev build-essential \
    && pip install --no-cache-dir playwright && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi "uvicorn[standard]" httpx
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
