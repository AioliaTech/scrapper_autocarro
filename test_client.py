"""
Cliente de teste para Universal Car Scraper API
"""

import asyncio
import httpx
import json
from datetime import datetime

class CarScraperClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def start_scrape(self, url: str, client_name: str = "test", **kwargs):
        """Inicia um job de scraping"""
        payload = {
            "url": url,
            "client_name": client_name,
            **kwargs
        }
        
        response = await self.client.post(f"{self.base_url}/scrape", json=payload)
        return response.json()
    
    async def get_job_status(self, job_id: str):
        """Consulta status de um job"""
        response = await self.client.get(f"{self.base_url}/job/{job_id}")
        return response.json()
    
    async def download_results(self, job_id: str, filename: str = None):
        """Download dos resultados"""
        response = await self.client.get(f"{self.base_url}/download/{job_id}")
        
        if not filename:
            filename = f"results_{job_id}.json"
        
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        return filename
    
    async def wait_for_completion(self, job_id: str, timeout: int = 300):
        """Aguarda conclusão de um job"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            status = await self.get_job_status(job_id)
            
            print(f"Status: {status['status']} - "
                  f"Encontrados: {status['stats']['total_found']} - "
                  f"Extraídos: {status['stats']['successfully_scraped']}")
            
            if status['status'] in ['completed', 'failed']:
                return status
            
            await asyncio.sleep(5)
        
        raise TimeoutError(f"Job {job_id} não concluído em {timeout}s")
    
    async def close(self):
        await self.client.aclose()

# Exemplo de uso
async def main():
    client = CarScraperClient()
    
    try:
        # Inicia scraping
        result = await client.start_scrape(
            url="https://m.autocarro.com.br/dekar",
            client_name="teste_autocarro",
            max_pages=5,
            delay_between_requests=1
        )
        
        job_id = result['job_id']
        print(f"🚀 Job iniciado: {job_id}")
        
        # Aguarda conclusão
        final_status = await client.wait_for_completion(job_id)
        
        if final_status['status'] == 'completed':
            print("✅ Scraping concluído!")
            
            # Download dos resultados
            filename = await client.download_results(job_id)
            print(f"📁 Resultados salvos em: {filename}")
            
            # Carrega e exibe resumo
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            print(f"\n📊 RESUMO:")
            print(f"Total encontrado: {data['stats']['total_found']}")
            print(f"Extraídos com sucesso: {data['stats']['successfully_scraped']}")
            print(f"Taxa de sucesso: {data['stats']['success_rate']}%")
            print(f"Duração: {data['stats']['duration']}")
            
            if data['cars']:
                print(f"\n🚗 PRIMEIRO CARRO:")
                car = data['cars'][0]
                print(f"Título: {car['titulo']}")
                print(f"Preço: {car['preco']}")
                print(f"Ano: {car['ano']}")
                print(f"KM: {car['quilometragem']}")
                print(f"Fotos: {car['total_fotos']}")
                print(f"Opcionais: {car['total_opcionais']}")
        
        else:
            print(f"❌ Falha no scraping: {final_status.get('error_message')}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
