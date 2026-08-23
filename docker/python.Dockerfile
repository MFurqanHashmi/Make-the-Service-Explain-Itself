FROM python:3.12.10-slim
WORKDIR /workspace
COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
