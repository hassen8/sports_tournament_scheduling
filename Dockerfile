FROM python:3.10-slim

# Set environment variables to non-interactive to avoid hanging during installs
ENV DEBIAN_FRONTEND=noninteractive

# -----------------------------------------------------------------------------
# 1. SYSTEM DEPENDENCIES
# -----------------------------------------------------------------------------
# Combined list of dependencies from both files. 
# Includes build tools (cmake, git, make), math libs (coinor, glpk, gmp), 
# and GUI/Display libs required by MiniZinc (libgl1, libxcb, etc).
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    unzip \
    git \
    cmake \
    ca-certificates \
    coinor-cbc \
    glpk-utils \
    libglpk40 \
    libedit2 \
    libtinfo6 \
    libc6 \
    libstdc++6 \
    libgl1 \
    libegl1 \
    libosmesa6 \
    libfontconfig1 \
    libfreetype6 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    libxrandr2 \
    libxi6 \
    libxfixes3 \
    libgpg-error0 \
    libgmp-dev \
    libffi-dev \
    libboost-dev \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-system-dev \
    zlib1g-dev \
    flex \
    bison \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# 2. SOLVER INSTALLATIONS (Friend's Requirements)
# -----------------------------------------------------------------------------

# Install Z3
RUN wget https://github.com/Z3Prover/z3/releases/download/z3-4.12.2/z3-4.12.2-x64-glibc-2.35.zip -O /tmp/z3.zip && \
    unzip /tmp/z3.zip -d /opt/z3 && \
    mv /opt/z3/z3-4.12.2-x64-glibc-2.35/bin/z3 /usr/local/bin/z3 && \
    chmod +x /usr/local/bin/z3 && rm -rf /tmp/z3.zip /opt/z3

# Install Yices
RUN wget https://yices.csl.sri.com/releases/2.6.2/yices-2.6.2-x86_64-pc-linux-gnu-static-gmp.tar.gz -O /tmp/yices.tar.gz && \
    tar -xzf /tmp/yices.tar.gz -C /opt && \
    mv /opt/yices-*/bin/yices /usr/local/bin/yices && \
    mv /opt/yices-*/bin/yices-smt2 /usr/local/bin/yices-smt2 && \
    chmod +x /usr/local/bin/yices* && rm -rf /tmp/yices.tar.gz /opt/yices-*

# Install Glucose (Compiled from source)
RUN git clone https://github.com/audemard/glucose.git /tmp/glucose && \
    cd /tmp/glucose/simp && make r && \
    mv /tmp/glucose/simp/glucose_release /usr/local/bin/glucose && \
    chmod +x /usr/local/bin/glucose && rm -rf /tmp/glucose

# Install OpenSMT (Compiled from source)
RUN git clone https://github.com/usi-verification-and-security/opensmt.git /tmp/opensmt && \
    mkdir /tmp/opensmt/build && cd /tmp/opensmt/build && \
    cmake .. && make -j4 && \
    cp opensmt /usr/local/bin/opensmt && chmod +x /usr/local/bin/opensmt && \
    rm -rf /tmp/opensmt

# -----------------------------------------------------------------------------
# 3. MINIZINC & AMPL (Your Requirements)
# -----------------------------------------------------------------------------

# Install MiniZinc
RUN wget https://github.com/MiniZinc/MiniZincIDE/releases/download/2.9.4/MiniZincIDE-2.9.4-bundle-linux-x86_64.tgz \
    && tar -xzf MiniZincIDE-2.9.4-bundle-linux-x86_64.tgz \
    && mv MiniZincIDE-2.9.4-bundle-linux-x86_64 /opt/minizinc \
    && rm MiniZincIDE-2.9.4-bundle-linux-x86_64.tgz

# Set MiniZinc Environment Variables
ENV PATH="/opt/minizinc/bin:$PATH"
ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/local/lib:usr/lib/x86_64-linux-gnu/:/opt/minizinc/lib"
ENV QT_PLUGIN_PATH="$QT_PLUGIN_PATH:/opt/minizinc/plugins"

# -----------------------------------------------------------------------------
# 4. PYTHON DEPENDENCIES
# -----------------------------------------------------------------------------

# Copy requirements file first to leverage Docker cache
COPY requirements.txt /tmp/requirements.txt

# Install Friend's requirements + Your manual pip installs
RUN pip install --no-cache-dir minizinc amplpy z3-solver python-sat pulp

# AMPL Setup
# Note: It is safer to pass API keys as env variables at runtime rather than baking into the image
ENV AMPL_KEY="12a37d81-e4ee-4e8d-935b-cca2c7497f70"
RUN python -m amplpy.modules install highs gurobi cplex && \
    python -m amplpy.modules activate ${AMPL_KEY}

# -----------------------------------------------------------------------------
# 5. PROJECT SETUP
# -----------------------------------------------------------------------------

WORKDIR /sports_tournament_scheduling

# Copy source code and resources
# We use COPY . . to ensure we capture all files from both projects, 
# assuming you have merged the folders locally.
COPY . .

# Fix potential Windows line endings in entry_point.sh (common issue when sharing code)
# and ensure it is executable
RUN chmod +x entry_point.sh

ENTRYPOINT ["./entry_point.sh"]

CMD []