FROM python:3.8-slim-buster

#Definindo variáveis de ambiente
ENV PORT=5000
ENV RUNNING_IN_DOCKER=True
#Para rodar localmente:
#ENV DJANGO_API_URL=http://localhost:8000/pt-br/problem_details
#Para rodar um container no docker-compose:
ENV DJANGO_API_URL=http://web:8020/pt-br/problem_details
WORKDIR /app

#Expondo a porta 5000
EXPOSE 5000

#Dependências para C e Julia
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.0-linux-x86_64.tar.gz | tar -xz -C /usr/local && \
    ln -s /usr/local/julia-1.9.0/bin/julia /usr/local/bin/julia

# Copiar dependências e código
COPY requirements.txt requirements.txt
COPY src/ . 
COPY bandit_config.yml .

#Instalar dependências do Python
RUN pip3 install --no-cache-dir -r requirements.txt

#Criar diretório para códigos
RUN mkdir code

#Configuração do Gunicorn
CMD gunicorn \
    --max-requests-jitter 0 \
    --bind 0.0.0.0:$PORT \
    --timeout 200 \
    -w 5 \
    'server:app'