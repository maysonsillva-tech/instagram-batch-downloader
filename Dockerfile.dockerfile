# Dockerfile
# Imagem base leve com Python
FROM python:3.12-slim

# Diretório de trabalho
WORKDIR /app

# Copia arquivos do projeto
COPY app.py index.html /app/

# Instala dependências
RUN pip install --no-cache-dir fastapi uvicorn yt-dlp requests

# Expõe a porta 80
EXPOSE 80

# Comando para rodar o app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]