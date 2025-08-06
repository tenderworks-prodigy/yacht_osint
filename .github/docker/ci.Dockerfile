FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python, Node.js LTS, Playwright deps and tooling
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y \
        python3.11 python3.11-distutils python3-pip git nodejs \
        libasound2 libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libgbm-dev \
        libnotify-dev libnss3 libxss1 libxtst6 ca-certificates wget && \
    npm install -g playwright && \
    npx playwright install-deps && \
    npx playwright install && \
    rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Install Python dependencies and dev tools
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r /tmp/requirements.txt ruff==0.12.5 black coverage[toml] && \
    rm /tmp/requirements.txt

WORKDIR /workspace
