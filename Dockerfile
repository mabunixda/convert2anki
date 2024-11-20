FROM python:3.12

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libgl1 \
                        python3-poetry \
                        tesseract-ocr \ 
                        tesseract-ocr-osd \
                        tesseract-ocr-eng \
                        tesseract-ocr-spa \
                        && \
    useradd --create-home --home-dir /app app \
    && chown -R app:app /app

USER app 
ADD pyproject.toml poetry.lock .

RUN poetry install \ 
    && mkdir -p media/uploads media/downloads

VOLUME [ "/app/media", "/app/.cache" ]

USER app
ADD *.py .
ADD templates ./templates
ADD entrypoint.sh /

ENTRYPOINT [ "/entrypoint.sh" ]
CMD [ "poetry", "run",  "python3", "app.py" ]
