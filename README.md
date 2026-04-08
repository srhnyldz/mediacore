# YLZ MediaCore

YLZ MediaCore is a Docker-first backend foundation for a future SaaS product that downloads media from supported social platforms and prepares the system for later conversion workflows.

## Highlights

- FastAPI-based API service for accepting download requests
- Celery worker service separated from the API process
- Redis used as broker and result backend
- `yt-dlp` integration for media retrieval
- `ffmpeg` baked into the worker image for future conversion pipelines
- Shared temporary download volume for API and worker coordination

## Project Structure

- `app/`: application code for API, workers, tasks, schemas, and utilities
- `docker/`: Dockerfiles for API and worker containers
- `docs/`: project definition, roadmap, and implementation notes
- `tests/`: bootstrap test coverage and validation scaffolding
- `storage/`: notes about the shared temporary storage strategy

## Quick Start

1. Copy `.env.example` to `.env`.
2. Build and start the stack with `docker compose up --build`.
3. Open the API docs at `http://localhost:8000/docs`.

## Local Validation

- Create a virtual environment with `make venv`
- Install dependencies with `make install`
- Run the unit test suite with `make test`
- Run syntax validation with `make compile`
- Start the full stack with `make up`
- Run an API smoke flow with `make smoke URL="https://example.com/video"`
- Stop the stack with `make down`

## Core Endpoints

- `POST /api/v1/tasks/downloads`: enqueue a new download task
- `GET /api/v1/tasks/{task_id}`: fetch the current task status and result metadata

## Versioning

This repository is currently at `v0.2.0` and follows `MAJOR.MINOR.PATCH`.

## Legal Notice

This project is provided for lawful use only. You are solely responsible for ensuring that any media download, conversion, storage, or redistribution complies with applicable laws, platform terms of service, copyright rules, and any required permissions in your jurisdiction.
