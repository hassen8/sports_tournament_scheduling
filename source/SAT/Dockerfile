FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget curl unzip git cmake ca-certificates \
    libgmp-dev libffi-dev libboost-dev && \
    rm -rf /var/lib/apt/lists/*

# Z3 CLI
RUN wget https://github.com/Z3Prover/z3/releases/download/z3-4.12.2/z3-4.12.2-x64-glibc-2.35.zip -O /tmp/z3.zip && \
    unzip /tmp/z3.zip -d /opt/z3 && \
    mv /opt/z3/z3-4.12.2-x64-glibc-2.35/bin/z3 /usr/local/bin/z3 && \
    chmod +x /usr/local/bin/z3 && \
    rm -rf /tmp/z3.zip /opt/z3

# CVC5
#RUN wget https://github.com/cvc5/cvc5/releases/download/cvc5-1.1.2/cvc5-Linux-x86_64-static -O /usr/local/bin/cvc5 && \
#    chmod +x /usr/local/bin/cvc5

# Yices 2.6.2
RUN wget https://yices.csl.sri.com/releases/2.6.2/yices-2.6.2-x86_64-pc-linux-gnu-static-gmp.tar.gz -O /tmp/yices.tar.gz && \
    tar -xzf /tmp/yices.tar.gz -C /opt && \
    mv /opt/yices-*/bin/yices /usr/local/bin/yices && \
    mv /opt/yices-*/bin/yices-smt2 /usr/local/bin/yices-smt2 && \
    chmod +x /usr/local/bin/yices* && \
    rm -rf /tmp/yices.tar.gz /opt/yices-*

# OpenSMT 2.7.0 
RUN wget https://github.com/usi-verification-and-security/opensmt/releases/download/v2.7.0/opensmt-2.7.0-x64-linux.tar.bz2 -O /tmp/opensmt.tar.bz2 && \
    tar -xf /tmp/opensmt.tar.bz2 -C /opt && \
    cp /opt/opensmt*/opensmt /usr/local/bin/opensmt && \
    chmod +x /usr/local/bin/opensmt && \
    rm -rf /tmp/opensmt.tar.bz2 /opt/opensmt*


# Open-WBO
RUN wget https://sat.inesc-id.pt/~mikolas/sw/open-wbo-2.0-linux -O /usr/local/bin/open-wbo && \
    chmod +x /usr/local/bin/open-wbo

# Glucose
RUN git clone https://github.com/audemard/glucose.git /tmp/glucose && \
    cd /tmp/glucose/simp && make r && \
    mv /tmp/glucose/simp/glucose_release /usr/local/bin/glucose && \
    chmod +x /usr/local/bin/glucose && \
    rm -rf /tmp/glucose

# Python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy project
WORKDIR /sports_tournament_scheduling
COPY . .

# Entrypoint
RUN sed -i 's/\r$//' entry_point.sh && chmod +x entry_point.sh
ENTRYPOINT ["./entry_point.sh"]
CMD []
