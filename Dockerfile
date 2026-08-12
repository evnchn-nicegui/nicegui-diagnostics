FROM python:3.12-slim

WORKDIR /app

# Install system deps for NiceGUI
RUN apt-get update && apt-get install -y --no-install-recommends \
    libegl1 libopengl0 && \
    rm -rf /var/lib/apt/lists/*

# Copy package
COPY pyproject.toml .
COPY src/ src/
COPY demo/ demo/
COPY README.md .

# Install package
RUN pip install --no-cache-dir -e .

EXPOSE 8081

CMD ["python", "demo/main.py"]
