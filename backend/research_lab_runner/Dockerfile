FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /runner
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 lab
COPY app.py .
RUN mkdir -p /run/research-lab \
    && chown -R lab:lab /runner /run/research-lab

USER lab
CMD ["python", "-I", "app.py", "--socket", "/run/research-lab/runner.sock"]
