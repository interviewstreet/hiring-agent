FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# hiring-agent.sh mounts your working folder and runs from there, so cache/ and
# scores.csv land next to your files rather than inside the image.
ENTRYPOINT ["python"]
CMD ["/app/batch_score.py", "--help"]
