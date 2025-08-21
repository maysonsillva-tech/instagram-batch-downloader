# app.py
# Backend simples para processar múltiplos links do Instagram e retornar metadados/URLs de download.
# Usa yt-dlp para extrair info sem baixar arquivos no servidor.
# Proxy para thumbnails e vídeos (com stream e attachment para forçar download).
# Correção: Content-Type dinâmico para thumbnails.
# Requisitos: pip install fastapi uvicorn yt-dlp requests

import subprocess
import json
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import uvicorn
import requests

app = FastAPI()

class LinksRequest(BaseModel):
    links: List[str]

def get_instagram_info(url: str) -> dict:
    """
    Executa yt-dlp --dump-json para obter metadados do vídeo (thumbnail, uploader, url direta).
    Retorna dict com os dados ou erro se falhar.
    """
    try:
        # Executa yt-dlp e captura o JSON
        result = subprocess.run(['yt-dlp', '--dump-json', url], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Extrai campos relevantes
        video_url = data.get('url')  # URL direta do vídeo (mp4)
        if not video_url and 'formats' in data and data['formats']:
            video_url = data['formats'][-1]['url']  # Pega o melhor formato se 'url' não estiver presente
        
        return {
            'thumbnail': data.get('thumbnail'),
            'uploader': data.get('uploader'),
            'url': video_url,
            'title': data.get('title', 'video')  # Título para nome do arquivo
        }
    except subprocess.CalledProcessError as e:
        return {'error': f'Erro ao processar {url}: {e.stderr}'}
    except Exception as e:
        return {'error': f'Erro inesperado em {url}: {str(e)}'}

@app.post("/download")
async def download_links(request: LinksRequest):
    """
    Recebe lista de links, processa cada um e retorna lista de resultados.
    Processa em sequência para evitar sobrecarga (yt-dlp pode ter rate limits).
    """
    results = []
    for url in request.links:
        if url.strip():  # Ignora linhas vazias
            info = get_instagram_info(url)
            results.append(info)
    return results

@app.get("/proxy-thumbnail")
async def proxy_thumbnail(url: str):
    """
    Proxy para thumbnails: Baixa a imagem e serve para evitar CORS, com Content-Type dinâmico.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            return Response(content=response.content, media_type=content_type)
        else:
            print(f"Erro no proxy thumbnail: {response.status_code} para {url}")  # Log para depuração
            raise HTTPException(status_code=response.status_code, detail="Falha ao carregar thumbnail")
    except Exception as e:
        print(f"Exceção no proxy thumbnail: {str(e)}")  # Log para depuração
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-video")
async def download_video(url: str, filename: str):
    """
    Proxy para vídeos: Stream o conteúdo com header de attachment para forçar download.
    """
    def iter_stream():
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        with requests.get(url, stream=True, headers=headers) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                yield chunk

    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': 'video/mp4'
    }
    return StreamingResponse(iter_stream(), headers=headers)

# Monte o StaticFiles DEPOIS dos endpoints para evitar conflitos
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    # Rode localmente: python app.py
    uvicorn.run(app, host="0.0.0.0", port=8000)