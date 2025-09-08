# Dockerfile estável - usa imagem oficial do Playwright
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Criar usuário
RUN groupadd -r app && useradd -r -g app app

# Diretório de trabalho
WORKDIR /app

# Instalar curl para health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY main.py .

# Criar diretórios
RUN mkdir -p /app/data /app/logs

# Permissões
RUN chown -R app:app /app
USER app

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando
CMD ["python", "main.py"]
