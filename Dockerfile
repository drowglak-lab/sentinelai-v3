# Переходим на стабильный LTS релиз (готовые бинарники обеспечат мгновенную сборку)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN adduser --disabled-password --gecos "" sentinel_user

WORKDIR /app

COPY core/requirements.txt .

# Установка пройдет мгновенно, так как pip скачает готовые wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R sentinel_user:sentinel_user /app

USER sentinel_user

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
