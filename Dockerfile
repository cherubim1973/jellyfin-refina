# ==============================================================================
# Dockerfile para Jellyfin-refina
# Multi-stage / Slim Python 3.11 com usuário não-root e healthcheck integrado
# ==============================================================================
FROM python:3.11-slim

# Metadados
LABEL maintainer="Nelson Cherubim de Andrade"
LABEL description="Jellyfin-refina: Catalogação, Auditoria e Curadoria Multimídia"

# Evita buffering de saída e geração de .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8585 \
    DATA_DIR=/app/data

# Instala curl para o Healthcheck e dependências do SO mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário e grupo não-root para execução segura (UID/GID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Diretório de trabalho
WORKDIR /app

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY app/ ./app/

# Cria diretório de dados persistentes e pontos de montagem de mídia com permissões adequadas
RUN mkdir -p /app/data /media/filmes /media/series /media/shows && \
    chown -R appuser:appgroup /app /media

# Alterna para o usuário não-root
USER appuser

# Expõe a porta 8585 (respeitando a regra de portas não conflitantes)
EXPOSE 8585

# Healthcheck interno via curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8585/health || exit 1

# Comando de inicialização do servidor Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8585"]
