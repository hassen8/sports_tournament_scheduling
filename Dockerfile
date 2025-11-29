FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        curl \
        unzip \
        ca-certificates \
        libgmp-dev \
        libboost-all-dev \
        libffi-dev \
        libstdc++6 \
        && rm -rf /var/lib/apt/lists/*


# Install Z3
RUN wget https://github.com/Z3Prover/z3/releases/download/z3-4.12.2/z3-4.12.2-x64-glibc-2.31.zip -O /tmp/z3.zip && \
    unzip /tmp/z3.zip -d /opt/z3 && \
    cp /opt/z3/bin/z3 /usr/local/bin/z3 && \
    chmod +x /usr/local/bin/z3 && \
    rm -rf /tmp/z3.zip


# Install CVC5 (static binary)
RUN wget https://github.com/cvc5/cvc5/releases/download/cvc5-1.1.2/cvc5-Linux-x86_64-static -O /usr/local/bin/cvc5 && \
    chmod +x /usr/local/bin/cvc5

# Install Yices2
RUN wget https://yices.csl.sri.com/releases/2.6.4/yices-2.6.4-x86_64-pc-linux-gnu-static-gmp.tar.gz -O /tmp/yices.tar.gz && \
    tar -xzf /tmp/yices.tar.gz -C /opt && \
    cp /opt/yices-*/bin/yices /usr/local/bin/yices && \
    cp /opt/yices-*/bin/yices-smt2 /usr/local/bin/yices-smt2 && \
    chmod +x /usr/local/bin/yices* && \
    rm -rf /tmp/yices.tar.gz

# Install OpenSMT2
RUN wget https://github.com/usi-verification-and-security/opensmt/releases/download/v2.7.2/opensmt-2.7.2-linux-x64.tar.gz -O /tmp/opensmt.tar.gz && \
    tar -xzf /tmp/opensmt.tar.gz -C /opt && \
    cp /opt/opensmt*/bin/opensmt /usr/local/bin/opensmt && \
    chmod +x /usr/local/bin/opensmt && \
    rm -rf /tmp/opensmt.tar.gz

# Install Open-WBO (MaxSAT)
RUN wget https://sat.inesc-id.pt/~mikolas/sw/open-wbo-2.0-linux -O /usr/local/bin/open-wbo && \
    chmod +x /usr/local/bin/open-wbo

# nstall Glucose repo

RUN git clone https://github.com/audemard/glucose.git /tmp/glucose && \
    cd /tmp/glucose/simp && \
    make r && \
    cp glucose /usr/local/bin/glucose && \
    chmod +x /usr/local/bin/glucose && \
    rm -rf /tmp/glucose


# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 
WORKDIR /sports_tournament_scheduling
COPY . .

# Entrypoint
RUN chmod +x entry_point.sh
ENTRYPOINT ["./entry_point.sh"]

CMD []
