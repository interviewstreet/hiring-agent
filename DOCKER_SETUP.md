# Docker Setup for Local Development

This guide explains how to use Docker and Docker Compose to run the Hiring Agent locally.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Quick Start

### 1. Setup environment variables

Copy the `.env.example` file to `.env` and configure as needed:

```bash
cp .env.example .env
```

Edit `.env` to set your preferences:

```env
# Use Ollama for local LLM (default)
LLM_PROVIDER=ollama
DEFAULT_MODEL=gemma3:4b

# OR use Google Gemini (requires API key)
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your_api_key_here
```

### 2. Start the services

Build and start both the app and Ollama services:

```bash
docker-compose up -d
```

This will:
- Build the hiring-agent application image
- Start the Ollama service and pull the default model
- Create a shared network between services

### 3. Access the app container

Enter the app container shell:

```bash
docker-compose exec app bash
```

### 4. Run the hiring agent

Inside the container, you can now run:

```bash
# Process a resume
python score.py /path/to/resume.pdf 

# Or run other modules as needed
python -c "from score import main; main()"
```

## Using Different LLM Providers

### With Ollama (Default, Recommended for Local Development)

The docker-compose setup includes an Ollama service that automatically pulls your configured model on startup. No additional setup needed beyond `.env` configuration.

### With Google Gemini

1. Get your API key from [Google AI Studio](https://aistudio.google.com/api-keys)
2. Update `.env`:
   ```env
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_actual_api_key
   ```
3. Remove the Ollama service dependency (optional):
   ```bash
   docker-compose up -d --no-deps app
   ```

## Volume Mounts

The setup mounts:
- `.:/app` - Your entire project directory (for hot-reload during development)
- `./cache:/app/cache` - GitHub and resume cache files (persisted across container runs)
- `ollama_data:/app/root/.ollama` - Ollama model data (persisted across container runs)

## Development Workflow

1. **Make code changes** locally in your IDE
2. **Changes are immediately reflected** in the container (due to volume mount)
3. **Restart containers only when** changing dependencies or Docker config

For Python changes, no rebuild needed. For dependency updates:

```bash
# Update requirements.txt, then rebuild
docker-compose up -d --build
```

## Performance Notes

- **First run**: Ollama will download the model (~2-10GB depending on model size)
- **Subsequent runs**: Much faster as model is cached

## Troubleshooting

### Ollama fails to pull model

```bash
# Check Ollama logs
docker-compose logs ollama

# Manually pull model after services are running
docker-compose exec ollama ollama pull gemma3:4b
```

### Connection refused errors

Ensure Ollama is fully ready before running the app:

```bash
# Check Ollama health
docker-compose exec ollama curl http://localhost:11434/api/tags
```

### Out of disk space

Ollama models can be large. Ensure adequate disk space:

```bash
# Clean up unused Docker resources
docker system prune -a --volumes
```
