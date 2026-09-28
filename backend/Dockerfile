FROM python:3.11-slim

WORKDIR /app

# tesseract-ocr: the local OCR engine backing app/document_processing/ocr_tesseract.py
# (see docs/decisions/007-ocr.md). tesseract-ocr-eng is usually pulled in
# automatically but is listed explicitly so English-language data is
# guaranteed present regardless of the base image's default dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
