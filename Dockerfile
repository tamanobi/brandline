# syntax = docker/dockerfile:experimental
FROM python:3.11-slim
RUN apt-get update -y && apt-get install -y ca-certificates fuse3 sqlite3 zip curl bash tmux
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,mode=0777,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x ./overmind
CMD ["./overmind", "start"]

