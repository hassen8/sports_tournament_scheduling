
FROM python:3.10-slim

ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV DEBIAN_FRONTEND=noninteractive


RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip && \
    python -m pip install amplpy


RUN python -m amplpy.modules install highs gurobi cplex


ENV AMPL_KEY="12a37d81-e4ee-4e8d-935b-cca2c7497f70"
RUN python -m amplpy.modules activate ${AMPL_KEY}


WORKDIR /app

COPY . /app/

CMD ["/bin/bash"]
