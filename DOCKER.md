# Docker Setup for Hiring Agent

This guide explains how to run the Hiring Agent application using Docker and Docker Compose.

**Note**: Hiring Agent is a **CLI tool**, not a web application. Docker is used to provide a standardized environment, not to run a server.

## Prerequisites

- Docker installed (https://docs.docker.com/get-docker/)
- Docker Compose installed (usually included with Docker Desktop)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/interviewstreet/hiring-agent.git
cd hiring-agent
```

### 2. Configure environment

Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

Edit `.env` to configure your LLM providers (Ollama, Gemini, etc.).

### 3. Build the Docker images

```bash
docker-compose build
```

### 4. Start the Ollama service (for local LLM)

```bash
docker-compose up -d ollama
```

This starts only the Ollama service in the background.

### 5. Use the CLI tool

#### Option A: Run single command

```bash
# Show help
docker-compose run app python evaluator.py --help

# Evaluate a resume (mount resumes directory)
docker-compose run -v $(pwd)/resumes:/app/resumes app python evaluator.py --resume resumes/sample.pdf

# Use with Ollama (default)
docker-compose run app python evaluator.py --resume resumes/sample.pdf --provider ollama
```

#### Option B: Enter interactive shell

```bash
# Enter the container shell
docker-compose run app bash

# Then run commands inside the container
python evaluator.py --help
python evaluator.py --resume resumes/sample.pdf
```

#### Option C: Start all services and exec into container

```bash
# Start all services in background
docker-compose up -d

# Exec into the app container
docker-compose exec app bash

# Run commands
python evaluator.py --resume resumes/sample.pdf

# Exit when done
exit

# Stop services
docker-compose down
```

## Usage Examples

### Example 1: Evaluate a resume with Ollama (local LLM)

```bash
# Start Ollama service
docker-compose up -d ollama

# Wait for Ollama to be ready (check logs)
docker-compose logs -f ollama

# Evaluate resume
docker-compose run app python evaluator.py \
  --resume resumes/sample.pdf \
  --provider ollama \
  --model llama3
```

### Example 2: Evaluate a resume with Gemini (cloud LLM)

```bash
# Configure .env with Gemini API key
# GEMINI_API_KEY=your_api_key

# Evaluate resume (no need to start Ollama)
docker-compose run app python evaluator.py \
  --resume resumes/sample.pdf \
  --provider gemini \
  --model gemini-pro
```

### Example 3: Batch evaluate multiple resumes

```bash
# Place resumes in ./resumes directory
# Then run batch evaluation
docker-compose run app bash -c "for pdf in resumes/*.pdf; do python evaluator.py --resume \$pdf; done"
```

## Common Commands

```bash
# Build images
docker-compose build

# Start all services
docker-compose up

# Start in detached mode (background)
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f app
docker-compose logs -f ollama

# Execute commands inside running container
docker-compose exec app bash
docker-compose exec ollama bash

# Run one-off command
docker-compose run app python evaluator.py --help

# Remove containers and networks
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v
```

## Ollama Integration

### Pull additional models

```bash
# Enter Ollama container
docker-compose exec ollama bash

# Pull models
ollama pull llama3
ollama pull mistral
ollama pull codellama

# List installed models
ollama list

# Exit container
exit
```

### Check Ollama status

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# View Ollama logs
docker-compose logs -f ollama
```

### Use custom Ollama model

Edit `docker-compose.yml` to change the default model:

```yaml
ollama:
  # ... other config
  command: >
    sh -c "ollama serve &
     sleep 5 &&
     ollama pull mistral ||  # Change model here
     true &&
     wait"
```

## Development

For development with live code reloading:

1. Mount your local code as a volume in `docker-compose.yml`:
   ```yaml
   services:
     app:
       volumes:
         - .:/app  # Mount current directory
         - ./data:/app/data
   ```

2. Rebuild after code changes:
   ```bash
   docker-compose up --build
   ```

## Troubleshooting

### Ollama model pull fails

If the default model pull fails during startup:

1. Access the Ollama container:
   ```bash
   docker-compose exec ollama bash
   ```

2. Manually pull a model:
   ```bash
   ollama pull llama3
   ```

3. Exit and restart services:
   ```bash
   exit
   docker-compose restart
   ```

### Permission issues

If you encounter permission issues with mounted volumes:

- On Linux: Make sure your user owns the `data/` and `resumes/` directories
- On Windows/Mac: Check Docker Desktop file sharing settings

### Out of memory

If Ollama fails to load models:

- Open Docker Desktop settings
- Increase memory allocation (recommend 8GB+ for running LLMs)
- Restart Docker

### .env file not found

If you see this error:
```
env file .env not found
```

Solution:
```bash
cp .env.example .env
```

### Command not found

If you see this error inside container:
```
python: command not found
```

Solution: Rebuild the image
```bash
docker-compose build --no-cache
```

## Project Structure with Docker

```
hiring-agent/
├── Dockerfile              # App container config
├── docker-compose.yml      # Multi-service orchestration
├── .dockerignore          # Build context exclusions
├── DOCKER.md              # This file
├── .env                   # Environment variables (create from .env.example)
├── resumes/               # Mount resumes here for evaluation
└── data/                  # Persist evaluation results
```

## Contributing

When contributing Docker-related changes:

1. Test that the Docker setup works on your machine
2. Update this document if you change the Docker configuration
3. Make sure `.dockerignore` excludes unnecessary files
4. Test both Ollama and cloud LLM providers

## License

Same as the main project license.
