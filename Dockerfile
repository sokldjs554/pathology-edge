FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv python3-dev g++ git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" CC=gcc CXX=g++
WORKDIR /app
COPY requirements-lock.txt /app/
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-lock.txt
COPY . /app
RUN pip install --no-deps --no-build-isolation -e .
EXPOSE 8000
CMD ["python", "-m", "http.server", "8000", "--directory", "dist", "--bind", "0.0.0.0"]
