FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir /app \
 && groupadd --gid 1000 bot \
 && useradd --uid 1000 --gid 1000 -m bot \
 && chmod 700 -R /app \
 && chown bot:bot -R /app

WORKDIR /app

USER bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm -f requirements.txt

COPY . .

CMD ["python", "main.py"]
