#FROM julia:1.10.10-alpine3.22 as julia-builder

FROM python:3.14-slim-bookworm

ENV PORT=5000 \
    RUNNING_IN_DOCKER=True

#Definindo variáveis de build para a versão do Julia
ARG JULIA_VERSION=1.9.0
ARG JULIA_MAJOR_MINOR=1.9

WORKDIR /app

#Instalando 'gcc' e 'libc6-dev' em vez do 'build-essential' completo para manter a imagem final o menor possível
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    #build-essential \
    gcc \
    libc6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#Instala Julia e remove arquivos desnecessários para economizar espaço.
RUN curl -sSL https://julialang-s3.julialang.org/bin/linux/x64/${JULIA_MAJOR_MINOR}/julia-${JULIA_VERSION}-linux-x86_64.tar.gz | tar -xz -C /usr/local && \
    ln -s /usr/local/julia-${JULIA_VERSION}/bin/julia /usr/local/bin/julia && \
    rm -rf /usr/local/julia-${JULIA_VERSION}/share/doc /usr/local/julia-${JULIA_VERSION}/share/man

#COPY --from=julia-builder /usr/local/julia /usr/local/julia
#RUN ln -s /usr/local/julia/bin/julia /usr/local/bin/julia

#Cria um grupo e um usuário não-root para rodar a aplicação (boa prática de segurança)
#RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home --shell /bin/bash appuser

# Define o diretório de trabalho final AGORA, ANTES de copiar qualquer coisa.
#WORKDIR /home/appuser/app

# Copia os arquivos de dependência PARA o novo WORKDIR
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte e outros arquivos, definindo as permissões. O "." agora se refere corretamente a /home/appuser/app
#COPY --chown=appuser:appgroup src/ .
#COPY --chown=appuser:appgroup bandit_config.yml .

COPY src/ .
COPY bandit_config.yml .

#Define a propriedade dos arquivos para o usuário não-root
#RUN chown -R appuser:appgroup /home/appuser/app
#USER appuser

RUN mkdir code

#Expõe a porta que a aplicação vai usar.
EXPOSE 5000

#Configuração do Gunicorn
CMD gunicorn \
    --max-requests-jitter 0 \
    --bind 0.0.0.0:$PORT \
    --timeout 200 \
    -w 11 \
    'server:app'