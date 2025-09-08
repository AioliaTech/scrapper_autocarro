echo "🚗 Iniciando Universal Car Scraper API..."

# Verificar se Playwright está instalado
if ! command -v playwright &> /dev/null; then
    echo "Instalando Playwright..."
    playwright install chromium
fi

# Criar diretórios se não existirem
mkdir -p data logs

# Instalar dependências se necessário
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Ativar ambiente virtual
source venv/bin/activate

# Iniciar servidor
echo "🚀 Iniciando servidor na porta 8000..."
python main.py
