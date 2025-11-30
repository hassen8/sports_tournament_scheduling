FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget curl unzip git cmake ca-certificates \
    libgmp-dev libffi-dev \
    libboost-dev \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-system-dev \
    zlib1g-dev \
    flex bison python3-dev \
    && rm -rf /var/lib/apt/lists/*


# Z3 
RUN wget https://github.com/Z3Prover/z3/releases/download/z3-4.12.2/z3-4.12.2-x64-glibc-2.35.zip -O /tmp/z3.zip && \
    unzip /tmp/z3.zip -d /opt/z3 && \
    mv /opt/z3/z3-4.12.2-x64-glibc-2.35/bin/z3 /usr/local/bin/z3 && \
    chmod +x /usr/local/bin/z3 && rm -rf /tmp/z3.zip /opt/z3

# Yices 
RUN wget https://yices.csl.sri.com/releases/2.6.2/yices-2.6.2-x86_64-pc-linux-gnu-static-gmp.tar.gz -O /tmp/yices.tar.gz && \
    tar -xzf /tmp/yices.tar.gz -C /opt && \
    mv /opt/yices-*/bin/yices /usr/local/bin/yices && \
    mv /opt/yices-*/bin/yices-smt2 /usr/local/bin/yices-smt2 && \
    chmod +x /usr/local/bin/yices* && rm -rf /tmp/yices.tar.gz /opt/yices-*

# Glucose 
RUN git clone https://github.com/audemard/glucose.git /tmp/glucose && \
    cd /tmp/glucose/simp && make r && \
    mv /tmp/glucose/simp/glucose_release /usr/local/bin/glucose && \
    chmod +x /usr/local/bin/glucose && rm -rf /tmp/glucose

# OpenSMT 
RUN git clone https://github.com/usi-verification-and-security/opensmt.git /tmp/opensmt && \
    mkdir /tmp/opensmt/build && cd /tmp/opensmt/build && \
    cmake .. && make -j4 && \
    cp opensmt /usr/local/bin/opensmt && chmod +x /usr/local/bin/opensmt && \
    rm -rf /tmp/opensmt

# Python deps
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Project files 
WORKDIR /sports_tournament_scheduling
COPY . .

RUN sed -i 's/\r$//' entry_point.sh && chmod +x entry_point.sh

ENTRYPOINT ["./entry_point.sh"]
CMD []
