#!/usr/bin/env python3
"""
Universal Car Scraper API - Versão Completa
Extrai dados detalhados de qualquer site de carros via webhook
Otimizado para Autocarro.com.br e sites similares
"""

import asyncio
import json
import logging
import os
import uuid
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, validator
from playwright.async_api import async_playwright, Page, Browser
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# =============================================================================
# MODELS
# =============================================================================

class ScrapeRequest(BaseModel):
    url: HttpUrl
    client_name: str = "default"
    custom_selectors: Optional[Dict[str, List[str]]] = None
    max_pages: int = 50
    delay_between_requests: int = 2
    extract_images: bool = True
    webhook_callback: Optional[HttpUrl] = None
    extract_optionals: bool = True

class ScrapeJob(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    url: str
    client_name: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_found: int = 0
    successfully_scraped: int = 0
    errors: int = 0
    result_file: Optional[str] = None
    error_message: Optional[str] = None

# =============================================================================
# UNIVERSAL CAR SCRAPER
# =============================================================================

class UniversalCarScraper:
    def __init__(self, job_id: str, config: Dict):
        self.job_id = job_id
        self.config = config
        self.setup_logging()
        self.cars_data = []
        self.job_stats = {
            'total_found': 0,
            'successfully_scraped': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def setup_logging(self):
        Path('logs').mkdir(exist_ok=True)
        self.logger = logging.getLogger(f"scraper_{self.job_id}")
        handler = logging.FileHandler(f'logs/job_{self.job_id}.log', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def get_autocarro_selectors(self) -> Dict[str, List[str]]:
        """Seletores específicos para Autocarro.com.br baseados na imagem"""
        return {
            'car_links': [
                'a[href*="/anuncio/"]',
                'a[href*="/veiculo/"]',
                '.item-carro a',
                '.card-veiculo a',
                '.anuncio-item a'
            ],
            'price': [
                '.preco-valor',
                '.valor-venda', 
                '.price-container .valor',
                '[class*="prec"]',
                '.price-display'
            ],
            'title': [
                'h1.titulo-veiculo',
                'h1.car-title',
                '.vehicle-title h1',
                '.anuncio-titulo h1'
            ],
            'year': [
                '.ano-modelo',
                '.badge-ano',
                '.year-badge'
            ],
            'specs_icons': {
                'quilometragem': [
                    '.icon-km + span',
                    '.kilometragem-valor',
                    '[data-icon="km"] + span'
                ],
                'combustivel': [
                    '.icon-fuel + span',
                    '.combustivel-tipo',
                    '[data-icon="fuel"] + span'
                ],
                'cambio': [
                    '.icon-gear + span',
                    '.cambio-tipo',
                    '[data-icon="transmission"] + span'
                ],
                'cor': [
                    '.icon-color + span',
                    '.cor-veiculo',
                    '[data-icon="color"] + span'
                ],
                'placa': [
                    '.icon-plate + span',
                    '.placa-veiculo',
                    '[data-icon="plate"] + span'
                ],
                'portas': [
                    '.icon-doors + span',
                    '.numero-portas',
                    '[data-icon="doors"] + span'
                ]
            },
            'gallery_images': [
                '.gallery-container img',
                '.carousel-images img',
                '.vehicle-photos img',
                '.galeria-fotos img'
            ],
            'thumbnail_images': [
                '.thumbs-container img',
                '.thumbnail-gallery img',
                '.mini-fotos img'
            ],
            'optionals_section': [
                '.opcionais-lista',
                '.optional-items',
                '.vehicle-features',
                '.features-list'
            ],
            'contact_button': [
                '.btn-contato',
                '.enviar-proposta',
                '.contact-dealer',
                'button[onclick*="proposta"]'
            ],
            'dealer_info': [
                '.dealer-name',
                '.vendedor-nome',
                '.loja-nome'
            ]
        }
    
    def get_universal_selectors(self) -> Dict[str, List[str]]:
        """Seletores universais + específicos do Autocarro"""
        autocarro_selectors = self.get_autocarro_selectors()
        
        universal_selectors = {
            'car_links': [
                'a[href*="/veiculo/"]',
                'a[href*="/carro/"]',
                'a[href*="/automovel/"]',
                'a[href*="/anuncio/"]',
                'a[href*="/vehicle/"]',
                '.item-carro a',
                '.veiculo-item a',
                '.car-item a',
                '.anuncio-item a',
                '.vehicle-card a',
                '.card-veiculo a'
            ],
            'price': [
                '.preco', '.price', '.valor', '.preço',
                '[class*="prec"]', '[class*="valor"]', '[class*="price"]',
                '.price-value', '.car-price', '.veiculo-preco',
                '.price-container', '.valor-venda', '.preco-venda'
            ],
            'title': [
                'h1', '.titulo', '.title', '.nome-veiculo',
                '.car-title', '.vehicle-title', '.anuncio-titulo'
            ],
            'images': [
                '.galeria img', '.fotos img', '.gallery img',
                '.car-images img', '.vehicle-photos img',
                '.carousel img', '.slider img'
            ]
        }
        
        # Merge seletores do Autocarro
        for key, selectors in autocarro_selectors.items():
            if key in universal_selectors:
                universal_selectors[key] = selectors + universal_selectors[key]
            else:
                universal_selectors[key] = selectors
        
        # Merge com seletores customizados se fornecidos
        if self.config.get('custom_selectors'):
            for key, selectors in self.config['custom_selectors'].items():
                if key in universal_selectors:
                    universal_selectors[key].extend(selectors)
                else:
                    universal_selectors[key] = selectors
        
        return universal_selectors
    
    async def create_browser_context(self, playwright):
        """Cria contexto otimizado do navegador"""
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='pt-BR',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Safari/537.36'
        )
        
        return browser, context
    
    async def get_car_links(self, page: Page, base_url: str) -> List[str]:
        """Extrai links de carros de forma universal"""
        self.logger.info(f"Extraindo links de: {base_url}")
        
        try:
            await page.goto(base_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Scroll para carregar conteúdo lazy-loaded
            await page.evaluate("""
                async () => {
                    const distance = 300;
                    const delay = 200;
                    
                    for (let i = 0; i < 10; i++) {
                        window.scrollBy(0, distance);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                    
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            """)
            
            selectors = self.get_universal_selectors()['car_links']
            
            # Preparar seletores para JavaScript
            selectors_js = json.dumps(selectors)
            base_url_js = base_url.replace("'", "\\'")
            
            car_links = await page.evaluate(f"""
                (selectors) => {{
                    const links = new Set();
                    const baseUrl = '{base_url_js}';
                    
                    selectors.forEach(selector => {{
                        try {{
                            document.querySelectorAll(selector).forEach(link => {{
                                let href = link.getAttribute('href');
                                if (href) {{
                                    if (href.startsWith('/')) {{
                                        const url = new URL(baseUrl);
                                        href = url.protocol + '//' + url.host + href;
                                    }}
                                    
                                    if (href.includes('veiculo') || href.includes('carro') || 
                                        href.includes('anuncio') || href.includes('automovel')) {{
                                        links.add(href);
                                    }}
                                }}
                            }});
                        }} catch (e) {{
                            console.log('Erro no seletor:', selector, e);
                        }}
                    }});
                    
                    return Array.from(links);
                }}
            """, selectors)
            
            self.logger.info(f"Encontrados {len(car_links)} links")
            self.job_stats['total_found'] = len(car_links)
            
            return car_links[:self.config.get('max_pages', 50)]
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair links: {e}")
            return []
    
    async def extract_car_data(self, page: Page, url: str) -> Optional[Dict]:
        """Extrai dados detalhados baseado na estrutura do Autocarro"""
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await page.wait_for_timeout(3000)
            
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(1000)
            
            car_data = await page.evaluate("""
                () => {
                    const cleanText = (text) => {
                        return text ? text.trim().replace(/\\s+/g, ' ') : 'N/A';
                    };
                    
                    const findText = (selectorList) => {
                        for (let selector of selectorList) {
                            try {
                                const element = document.querySelector(selector);
                                if (element && element.textContent.trim()) {
                                    return cleanText(element.textContent);
                                }
                            } catch (e) {}
                        }
                        return 'N/A';
                    };
                    
                    const getPrice = () => {
                        const priceElements = document.querySelectorAll('.preco, .valor, .price, [class*="prec"]');
                        for (let el of priceElements) {
                            const text = el.textContent;
                            if (text && (text.includes('R$') || text.includes('$'))) {
                                return cleanText(text);
                            }
                        }
                        
                        const priceRegex = /R\\$\\s*[\\d.,]+/g;
                        const matches = document.body.textContent.match(priceRegex);
                        if (matches && matches.length > 0) {
                            return matches.reduce((a, b) => {
                                const aNum = parseFloat(a.replace(/[^\\d]/g, ''));
                                const bNum = parseFloat(b.replace(/[^\\d]/g, ''));
                                return aNum > bNum ? a : b;
                            });
                        }
                        return 'N/A';
                    };
                    
                    const getSpecsFromIcons = () => {
                        const specs = {};
                        
                        const iconPatterns = [
                            {key: 'quilometragem', regex: /([\\d.,]+)\\s*km/i},
                            {key: 'combustivel', values: ['flex', 'gasolina', 'etanol', 'diesel', 'gnv']},
                            {key: 'cambio', values: ['automático', 'manual', 'cvt']},
                            {key: 'ano', regex: /(19|20)\\d{2}\\/(19|20)\\d{2}|(19|20)\\d{2}/},
                            {key: 'portas', regex: /(\\d)\\s*portas?/i},
                            {key: 'cor', values: ['preta', 'branca', 'prata', 'vermelha', 'azul', 'cinza']},
                            {key: 'placa', regex: /[A-Z]{3}-?\\d{4}|[A-Z]{3}\\d[A-Z]\\d{2}/i}
                        ];
                        
                        const bodyText = document.body.textContent.toLowerCase();
                        
                        iconPatterns.forEach(pattern => {
                            if (pattern.regex) {
                                const match = bodyText.match(pattern.regex);
                                if (match) {
                                    specs[pattern.key] = match[0];
                                }
                            } else if (pattern.values) {
                                for (let value of pattern.values) {
                                    if (bodyText.includes(value)) {
                                        specs[pattern.key] = value;
                                        break;
                                    }
                                }
                            }
                        });
                        
                        return specs;
                    };
                    
                    const getAllImages = () => {
                        const images = new Set();
                        
                        const imgSelectors = [
                            'img[src*="autocarro"]',
                            '.gallery img',
                            '.carousel img', 
                            '.vehicle-photos img',
                            '.thumbs img',
                            'img[alt*="carro"]',
                            'img[alt*="veículo"]'
                        ];
                        
                        imgSelectors.forEach(selector => {
                            try {
                                document.querySelectorAll(selector).forEach(img => {
                                    let src = img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy');
                                    
                                    if (src && 
                                        (src.includes('.jpg') || src.includes('.jpeg') || 
                                         src.includes('.png') || src.includes('.webp')) &&
                                        !src.includes('logo') && !src.includes('icon') && 
                                        !src.includes('btn') && src.length > 20) {
                                        
                                        if (src.startsWith('/')) {
                                            src = window.location.origin + src;
                                        }
                                        
                                        images.add(src);
                                    }
                                });
                            } catch (e) {}
                        });
                        
                        return Array.from(images);
                    };
                    
                    const getOptionals = () => {
                        const optionals = [];
                        
                        const optionalSections = [
                            '.opcionais', '.optional', '.features', '.equipamentos',
                            '.acessorios', '.extras'
                        ];
                        
                        optionalSections.forEach(section => {
                            try {
                                const sectionEl = document.querySelector(section);
                                if (sectionEl) {
                                    const items = sectionEl.querySelectorAll('li, .item, span, p');
                                    items.forEach(item => {
                                        const text = cleanText(item.textContent);
                                        if (text && text.length > 2 && text.length < 50) {
                                            optionals.push(text);
                                        }
                                    });
                                }
                            } catch (e) {}
                        });
                        
                        if (optionals.length === 0) {
                            const commonOptionals = [
                                'air bag', 'abs', 'direção hidráulica', 'ar condicionado',
                                'vidros elétricos', 'travas elétricas', 'alarme', 'som',
                                'cd player', 'mp3', 'bluetooth', 'gps', 'câmera de ré',
                                'sensor de estacionamento', 'teto solar', 'banco de couro'
                            ];
                            
                            const bodyText = document.body.textContent.toLowerCase();
                            commonOptionals.forEach(optional => {
                                if (bodyText.includes(optional)) {
                                    optionals.push(optional);
                                }
                            });
                        }
                        
                        return [...new Set(optionals)].slice(0, 20);
                    };
                    
                    const getContactInfo = () => {
                        const contact = {};
                        
                        const phoneRegex = /\\(?\\d{2}\\)?\\s*\\d{4,5}-?\\d{4}/g;
                        const phoneMatches = document.body.textContent.match(phoneRegex);
                        if (phoneMatches) {
                            contact.telefone = phoneMatches[0];
                        }
                        
                        const whatsappLinks = document.querySelectorAll('a[href*="whatsapp"], a[href*="wa.me"]');
                        if (whatsappLinks.length > 0) {
                            const href = whatsappLinks[0].href;
                            const phoneMatch = href.match(/\\d{11,}/);
                            if (phoneMatch) {
                                contact.whatsapp = phoneMatch[0];
                            }
                        }
                        
                        return contact;
                    };
                    
                    const getTitle = () => {
                        const titleSelectors = [
                            'h1',
                            '.car-title', 
                            '.vehicle-title',
                            '.anuncio-titulo'
                        ];
                        
                        for (let selector of titleSelectors) {
                            const el = document.querySelector(selector);
                            if (el && el.textContent.trim()) {
                                return cleanText(el.textContent);
                            }
                        }
                        
                        return cleanText(document.title);
                    };
                    
                    const specs = getSpecsFromIcons();
                    const images = getAllImages();
                    const optionals = getOptionals();
                    const contact = getContactInfo();
                    
                    return {
                        url: window.location.href,
                        timestamp: new Date().toISOString(),
                        domain: window.location.hostname,
                        
                        titulo: getTitle(),
                        preco: getPrice(),
                        
                        marca: specs.marca || 'N/A',
                        modelo: specs.modelo || 'N/A', 
                        ano: specs.ano || 'N/A',
                        quilometragem: specs.quilometragem || 'N/A',
                        combustivel: specs.combustivel || 'N/A',
                        cambio: specs.cambio || 'N/A',
                        cor: specs.cor || 'N/A',
                        placa: specs.placa || 'N/A',
                        portas: specs.portas || 'N/A',
                        
                        cidade: 'N/A',
                        estado: 'N/A',
                        
                        fotos: images,
                        total_fotos: images.length,
                        
                        opcionais: optionals,
                        total_opcionais: optionals.length,
                        
                        telefone: contact.telefone || 'N/A',
                        whatsapp: contact.whatsapp || 'N/A',
                        
                        descricao: 'N/A',
                        vendedor: 'N/A',
                        
                        visitas: document.querySelector('.visitas')?.textContent || 'N/A',
                        
                        extracted_at: new Date().toISOString(),
                        extraction_success: true
                    };
                }
            """)
            
            # Pós-processamento para extrair marca/modelo do título
            if car_data['titulo'] != 'N/A':
                title_parts = car_data['titulo'].upper().split()
                if len(title_parts) >= 2:
                    car_data['marca'] = title_parts[0]
                    car_data['modelo'] = ' '.join(title_parts[1:3])
            
            self.job_stats['successfully_scraped'] += 1
            self.logger.info(f"✓ Extraído: {car_data['titulo'][:50]}...")
            
            return car_data
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair {url}: {e}")
            self.job_stats['errors'] += 1
            return None
    
    async def scrape_website(self, url: str) -> List[Dict]:
        """Função principal para fazer scrape de um site"""
        self.job_stats['start_time'] = datetime.now()
        self.logger.info(f"🚗 Iniciando scrape de {url}")
        
        async with async_playwright() as playwright:
            browser, context = await self.create_browser_context(playwright)
            page = await context.new_page()
            
            try:
                car_links = await self.get_car_links(page, url)
                
                if not car_links:
                    self.logger.warning("Nenhum link encontrado!")
                    return []
                
                for i, car_url in enumerate(car_links, 1):
                    self.logger.info(f"🔄 Processando {i}/{len(car_links)}: {car_url}")
                    
                    car_data = await self.extract_car_data(page, car_url)
                    if car_data:
                        self.cars_data.append(car_data)
                    
                    if i < len(car_links):
                        await asyncio.sleep(self.config.get('delay_between_requests', 2))
                
            except Exception as e:
                self.logger.error(f"Erro durante scraping: {e}")
                raise
            
            finally:
                await browser.close()
                self.job_stats['end_time'] = datetime.now()
        
        return self.cars_data

# =============================================================================
# API REST
# =============================================================================

app = FastAPI(
    title="Universal Car Scraper API",
    description="API para extrair dados detalhados de qualquer site de carros",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs_storage: Dict[str, ScrapeJob] = {}

@app.get("/")
async def root():
    return {
        "message": "Universal Car Scraper API",
        "version": "2.0.0",
        "status": "online",
        "endpoints": {
            "POST /scrape": "Inicia scraping de um site",
            "GET /job/{job_id}": "Status de um job",
            "GET /download/{job_id}": "Download dos resultados",
            "GET /jobs": "Lista todos os jobs"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "active_jobs": len([j for j in jobs_storage.values() if j.status == "running"])
    }

@app.post("/scrape", response_model=Dict[str, str])
async def start_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Inicia um job de scraping"""
    job_id = str(uuid.uuid4())
    
    job = ScrapeJob(
        job_id=job_id,
        status="pending",
        url=str(request.url),
        client_name=request.client_name,
        created_at=datetime.now()
    )
    
    jobs_storage[job_id] = job
    
    config = {
        'custom_selectors': request.custom_selectors,
        'max_pages': request.max_pages,
        'delay_between_requests': request.delay_between_requests,
        'extract_images': request.extract_images,
        'extract_optionals': request.extract_optionals,
        'webhook_callback': str(request.webhook_callback) if request.webhook_callback else None
    }
    
    background_tasks.add_task(run_scraping_job, job_id, str(request.url), config)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": f"Scraping iniciado para {request.url}",
        "check_status": f"/job/{job_id}"
    }

async def run_scraping_job(job_id: str, url: str, config: Dict):
    """Executa o job de scraping em background"""
    job = jobs_storage[job_id]
    
    try:
        job.status = "running"
        job.started_at = datetime.now()
        
        scraper = UniversalCarScraper(job_id, config)
        cars_data = await scraper.scrape_website(url)
        
        Path('data').mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = f'data/scrape_{job.client_name}_{timestamp}.json'
        
        result = {
            'job_id': job_id,
            'client_name': job.client_name,
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'stats': {
                'total_found': scraper.job_stats['total_found'],
                'successfully_scraped': scraper.job_stats['successfully_scraped'],
                'errors': scraper.job_stats['errors'],
                'success_rate': round((scraper.job_stats['successfully_scraped'] / max(scraper.job_stats['total_found'], 1)) * 100, 2),
                'duration': str(scraper.job_stats['end_time'] - scraper.job_stats['start_time'])
            },
            'cars': cars_data
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        job.status = "completed"
        job.completed_at = datetime.now()
        job.total_found = scraper.job_stats['total_found']
        job.successfully_scraped = scraper.job_stats['successfully_scraped']
        job.errors = scraper.job_stats['errors']
        job.result_file = result_file
        
        if config.get('webhook_callback'):
            await call_webhook(config['webhook_callback'], {
                'job_id': job_id,
                'status': 'completed',
                'total_cars': len(cars_data),
                'download_url': f'/download/{job_id}',
                'stats': result['stats']
            })
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now()

async def call_webhook(webhook_url: str, data: Dict):
    """Chama webhook de callback"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=data, timeout=10)
    except Exception as e:
        logging.error(f"Erro ao chamar webhook {webhook_url}: {e}")

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Retorna status de um job"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    job = jobs_storage[job_id]
    return {
        "job_id": job.job_id,
        "status": job.status,
        "client_name": job.client_name,
        "url": job.url,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "stats": {
            "total_found": job.total_found,
            "successfully_scraped": job.successfully_scraped,
            "errors": job.errors,
            "success_rate": round((job.successfully_scraped / max(job.total_found, 1)) * 100, 2) if job.total_found > 0 else 0
        },
        "error_message": job.error_message,
        "download_available": job.result_file is not None
    }

@app.get("/download/{job_id}")
async def download_results(job_id: str):
    """Download dos resultados de um job"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    job = jobs_storage[job_id]
    
    if job.status != "completed" or not job.result_file:
        raise HTTPException(status_code=400, detail="Job não concluído ou sem resultados")
    
    if not Path(job.result_file).exists():
        raise HTTPException(status_code=404, detail="Arquivo de resultados não encontrado")
    
    return FileResponse(
        job.result_file,
        media_type='application/json',
        filename=f"scrape_results_{job.client_name}_{job_id}.json"
    )

@app.get("/jobs")
async def list_jobs():
    """Lista todos os jobs"""
    jobs_list = []
    for job in jobs_storage.values():
        jobs_list.append({
            "job_id": job.job_id,
            "status": job.status,
            "client_name": job.client_name,
            "url": job.url,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "total_found": job.total_found,
            "successfully_scraped": job.successfully_scraped
        })
    
    return {
        "total_jobs": len(jobs_list),
        "jobs": sorted(jobs_list, key=lambda x: x['created_at'], reverse=True)
    }

@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Remove um job e seus arquivos"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    job = jobs_storage[job_id]
    
    # Remove arquivo de resultados se existir
    if job.result_file and Path(job.result_file).exists():
        Path(job.result_file).unlink()
    
    # Remove log file
    log_file = Path(f'logs/job_{job_id}.log')
    if log_file.exists():
        log_file.unlink()
    
    # Remove do storage
    del jobs_storage[job_id]
    
    return {"message": f"Job {job_id} removido com sucesso"}

@app.post("/test-selectors")
async def test_selectors(request: Dict[str, Any]):
    """Testa seletores customizados em uma URL específica"""
    url = request.get('url')
    selectors = request.get('selectors', {})
    
    if not url:
        raise HTTPException(status_code=400, detail="URL é obrigatória")
    
    config = {
        'custom_selectors': selectors,
        'max_pages': 1,
        'delay_between_requests': 0,
        'extract_images': True
    }
    
    test_job_id = f"test_{uuid.uuid4()}"
    scraper = UniversalCarScraper(test_job_id, config)
    
    async with async_playwright() as playwright:
        browser, context = await scraper.create_browser_context(playwright)
        page = await context.new_page()
        
        try:
            result = await scraper.extract_car_data(page, url)
            return {
                "url": url,
                "selectors_used": selectors,
                "extraction_result": result,
                "success": result is not None
            }
        except Exception as e:
            return {
                "url": url,
                "selectors_used": selectors,
                "error": str(e),
                "success": False
            }
        finally:
            await browser.close()

@app.post("/webhook/callback")
async def webhook_callback(data: Dict[str, Any]):
    """Exemplo de endpoint para receber callbacks"""
    print(f"📞 Webhook recebido: {data}")
    
    job_id = data.get('job_id')
    status = data.get('status')
    
    if status == 'completed':
        print(f"✅ Job {job_id} concluído com sucesso!")
        print(f"📊 Total de carros: {data.get('total_cars')}")
        print(f"📈 Estatísticas: {data.get('stats')}")
    
    return {"message": "Callback recebido com sucesso"}

@app.post("/webhook/n8n")
async def n8n_webhook_trigger(data: Dict[str, Any]):
    """Endpoint específico para triggers do N8N"""
    
    url = data.get('url')
    client_name = data.get('client_name', 'n8n_trigger')
    
    if not url:
        raise HTTPException(status_code=400, detail="URL é obrigatória")
    
    job_id = str(uuid.uuid4())
    
    job = ScrapeJob(
        job_id=job_id,
        status="pending",
        url=url,
        client_name=client_name,
        created_at=datetime.now()
    )
    
    jobs_storage[job_id] = job
    
    config = {
        'max_pages': data.get('max_pages', 50),
        'delay_between_requests': data.get('delay', 2),
        'extract_images': True,
        'extract_optionals': True,
        'webhook_callback': f"https://n8n-scrapper.xnvwew.easypanel.host/webhook/n8n/callback"
    }
    
    asyncio.create_task(run_scraping_job(job_id, url, config))
    
    return {
        "job_id": job_id,
        "status": "started", 
        "n8n_integration": True,
        "monitor_url": f"https://n8n-scrapper.xnvwew.easypanel.host/job/{job_id}",
        "download_url": f"https://n8n-scrapper.xnvwew.easypanel.host/download/{job_id}"
    }

@app.post("/webhook/n8n/callback")
async def n8n_callback_receiver(data: Dict[str, Any]):
    """Recebe callbacks e pode retornar para N8N"""
    print(f"📨 Callback recebido para N8N: {data}")
    
    return {
        "received": True,
        "job_id": data.get('job_id'),
        "status": data.get('status'),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """Métricas para monitoring"""
    jobs = list(jobs_storage.values())
    
    return {
        "total_jobs": len(jobs),
        "completed_jobs": len([j for j in jobs if j.status == "completed"]),
        "failed_jobs": len([j for j in jobs if j.status == "failed"]),
        "running_jobs": len([j for j in jobs if j.status == "running"]),
        "total_cars_scraped": sum(j.successfully_scraped for j in jobs),
        "average_success_rate": sum(
            j.successfully_scraped / max(j.total_found, 1) for j in jobs 
            if j.total_found > 0
        ) / max(len([j for j in jobs if j.total_found > 0]), 1) * 100 if jobs else 0
    }

@app.on_event("startup")
async def startup_event():
    """Configurações de inicialização"""
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    
    print("🚗 Universal Car Scraper API iniciada!")
    print("📚 Documentação: http://localhost:8000/docs")
    print("🏥 Health check: http://localhost:8000/health")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
