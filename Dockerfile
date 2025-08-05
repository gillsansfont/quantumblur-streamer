# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

# Install system dependencies for building Qiskit, OpenCV, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libgl1-mesa-glx \
      libglib2.0-0 \
      git \
    && rm -rf /var/lib/apt/lists/*

# Prevent Python from writing bytecode and disable pip cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Install GPU-accelerated Aer if available
    pip install qiskit-aer-gpu

# Stage 2: Runtime image
FROM python:3.11-slim

# Install minimal runtime system libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python environment variables for unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Limit thread pools for OpenMP and MKL to reduce context switching
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2

WORKDIR /app

# Copy only the installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /app

# Expose application port
EXPOSE 5000

# Use uvicorn with uvloop and the h11 HTTP backend, disable lifespan checks
CMD ["uvicorn", "app:app", 
     "--host", "0.0.0.0", 
     "--port", "5000", 
     "--loop", "uvloop", 
     "--http", "h11", 
     "--workers", "1", 
     "--lifespan", "off"]

