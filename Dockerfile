# syntax=docker/dockerfile:1
FROM python:3.11.4-slim as build

# Dir
WORKDIR /base

# ENV vars
ENV ENV='production'
ENV PORT=8080

# Move necessary files
COPY /src/ /base/app
COPY requirements.txt /base/requirements.txt

# Install deps
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

ENTRYPOINT ["python", "./app/main.py"]