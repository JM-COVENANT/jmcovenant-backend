FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Schrijfbare mappen in container
RUN mkdir -p data generated_pds

EXPOSE 5000

# Veel platforms zetten PORT; anders 5000
CMD ["sh", "-c", "waitress-serve --listen=0.0.0.0:${PORT:-5000} wsgi:app"]
