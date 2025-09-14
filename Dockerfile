FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
RUN mkdir -p /home/user/.cache/huggingface && \
    chown -R user:user /home/user/.cache

ENV HF_HOME=/home/user/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/user/.cache/huggingface
ENV HF_DATASETS_CACHE=/home/user/.cache/huggingface

COPY requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY app.py /code/app.py

RUN chown -R user:user /code

USER user

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]