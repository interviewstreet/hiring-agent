# Meritlab classification service. Separate deployment; never part of Meritlab's compose.
FROM python:3.11-slim

WORKDIR /app

# System deps for PyMuPDF and friends.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8100

# One worker keeps the in-memory job store coherent. For multiple workers, back the
# job store with a shared store (see the seam note in service.py) before scaling.
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8100"]
