FROM python:3.11-slim-bookworm AS build

RUN apt-get update \
    && apt-get install -y build-essential libpoppler-cpp-dev pkg-config ocrmypdf

RUN python3 -m pip install pipx \
    && pipx install --global poetry

WORKDIR /app

COPY . .

RUN poetry install --no-interaction

RUN poetry build

# # ============================================================================
FROM python:3.11-slim-bookworm AS prod

RUN apt-get update \
    && apt-get install -y build-essential libpoppler-cpp-dev pkg-config ocrmypdf

COPY --from=build /app/dist/*.whl /app/dist/

RUN python3 -m pip install pipx \
    && pipx install --global /app/dist/monopoly_core-0.13.6-py3-none-any.whl[ocr]

WORKDIR /tmp

ENTRYPOINT ["monopoly"]
