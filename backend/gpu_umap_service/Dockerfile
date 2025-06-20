FROM rapidsai/rapidsai-core:24.08-cuda12.0-runtime-ubuntu22.04-py3.9 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM rapidsai/rapidsai-core:24.08-cuda12.0-runtime-ubuntu22.04-py3.9
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 8001
CMD ["uvicorn","umap_service.main:app","--host","0.0.0.0","--port","8001"]
