FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN useradd --create-home --shell /bin/bash app

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores do Playwright
RUN playwright install chromium
RUN playwright install-deps

# Copiar código fonte
COPY main.py .
COPY .env.example .env

# Criar diretórios necessários
RUN mkdir -p /app/logs /app/data

# Definir permissões
RUN chown -R app:app /app
USER app

EXPOSE 8000

CMD ["python", "main.py"]
