# syntax = docker/dockerfile:experimental
FROM python:3.11-slim
RUN apt-get update -y && apt-get install -y ca-certificates fuse3 sqlite3 zip curl bash tmux
WORKDIR /app
RUN curl -L https://github.com/DarthSim/overmind/releases/download/v2.4.0/overmind-v2.4.0-linux-amd64.gz -o overmind-v2.4.0-linux-amd64.gz && gunzip overmind-v2.4.0-linux-amd64.gz && mv overmind-v2.4.0-linux-amd64 overmind
RUN chmod +x ./overmind
COPY requirements.txt .
RUN --mount=type=cache,mode=0777,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["./overmind", "start"]

