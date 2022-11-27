FROM python:3.11-slim as base

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1

FROM base AS python-deps

# Install pipenv and compilation dependencies
RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Install python dependencies in /.venv
COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

EXPOSE 8000

# Copy virtual env from python-deps stage
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Create and switch to a new user
RUN useradd --create-home chaintrap
WORKDIR /home/chaintrap
USER chaintrap

# Install application into container
COPY . .

# Run the application
# ENTRYPOINT ["python", "-m", "http.server"]
# CMD ["--directory", "directory", "8000"]
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--proxy-headers", "--port", "8000"]
