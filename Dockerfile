FROM python:3.10-slim

# System dependencies for SAT+SMT
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    unzip \
    ca-certificates \
    libgmp-dev \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

