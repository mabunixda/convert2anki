FROM python:3.12

WORKDIR /app

RUN pip3 install poetry
ADD pyproject.toml ./

RUN poetry install --no-root \ 
    && mkdir -p media/uploads

VOLUME [ "/app/media" ]

ADD *.py ./

ENV OPENAI_API_KEY=

CMD [ "poetry", "run",  "python3", "app.py" ]