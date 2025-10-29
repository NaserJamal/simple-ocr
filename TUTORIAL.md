# Building Custom Docker Images for ML Models

A step-by-step guide using Qwen Image Edit as a practical example.

## Overview

This tutorial walks you through creating production-ready Docker images for ML model deployment. We'll use the Qwen Image Edit model to demonstrate the key concepts and patterns.

---

## Project Structure

```
qwen-image-edit-image/
├── Dockerfile              # Container blueprint
├── requirements.txt        # Python dependencies
└── app/
    ├── main.py            # FastAPI application & endpoints
    ├── controllers/       # Request handling layer
    ├── services/          # Business logic & model inference
    └── models/            # Data models (Pydantic schemas)
```

**Architecture**: Clean separation between API layer (FastAPI), business logic (services), and request handling (controllers).

---

## Step 1: Choose the Right Base Image

```dockerfile
FROM cupy/cupy:v13.2.0
```

**Why this matters:**
- CuPy provides GPU-accelerated computing (CUDA + NumPy-compatible APIs)
- Pre-configured with CUDA drivers and dependencies
- Eliminates hours of environment setup

**For your model, ask:**
- Does it need GPU? → Use CUDA-enabled base images
- Specific frameworks? → Check official images (pytorch/pytorch, tensorflow/tensorflow)
- CPU-only inference? → Use lightweight Python images (python:3.11-slim)

---

## Step 2: Configure Python Environment

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
```

**What each does:**
- `PYTHONDONTWRITEBYTECODE=1`: Prevents `.pyc` files (reduces image size)
- `PYTHONUNBUFFERED=1`: Shows logs in real-time (critical for debugging)
- `PIP_NO_CACHE_DIR=1`: Skips pip cache (smaller image size)

---

## Step 3: Install Dependencies Efficiently

```dockerfile
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

**Why copy requirements.txt first?**
- Docker caches layers that haven't changed
- If you change code but not dependencies, Docker reuses the cached layer
- **Rebuilds are 10x faster**

**Key dependencies for this example:**
```txt
fastapi>=0.116.1           # Modern async web framework
uvicorn[standard]>=0.35.0  # ASGI server
diffusers==0.35.1          # Hugging Face pipelines
transformers==4.56.1       # Model architectures
torch + torchvision        # Deep learning framework
```

---

## Step 4: Security - Run as Non-Root User

```dockerfile
RUN groupadd -g 10000 runner && \
    useradd -m -u 10000 -g 10000 -s /bin/bash runner

COPY . .
RUN chown -R runner:runner /app

USER runner:runner
```

**Why this matters:**
- Running as root is a security risk
- If the container is compromised, damage is limited
- **Production requirement** for most platforms

**Pattern:**
1. Create user with specific UID/GID (10000)
2. Copy application code
3. Transfer ownership to non-root user
4. Switch to that user

---

## Step 5: Define Runtime Configuration

```dockerfile
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Breakdown:**
- `EXPOSE 8080`: Documents which port the app uses
- `CMD`: Default command when container starts
- `--host 0.0.0.0`: Listen on all network interfaces (required for Docker)
- `--port 8080`: Match your platform's expected port

---

## Step 6: Build the Application Code

### FastAPI Entrypoint (app/main.py)

```python
from fastapi import FastAPI
from app.controllers.ModelController import ModelController

model_controller = ModelController()
app = FastAPI(title="Qwen Image Edit API", version="0.1.0")

@app.get("/health-check")
async def health():
    return {"status": "ok"}

@app.post("/v1/images/edits")
async def edit_image(payload: EditRequestPayload):
    return await model_controller.edit_image(payload)
```

**Key patterns:**
- Health check endpoint (required for platform monitoring)
- Single controller instance (model loaded once at startup)
- Async handlers for non-blocking I/O

### Model Loading (app/services/ModelService.py)

```python
from diffusers import QwenImageEditPipeline
import torch

class ModelService:
    def __init__(self):
        self.__model = QwenImageEditPipeline.from_pretrained(
            "ovedrive/qwen-image-edit-4bit",
            torch_dtype=torch.bfloat16
        )
        self.__model.to("cuda")
```

**Critical decisions:**
- Model loaded at service initialization (not per-request)
- Using `bfloat16` for faster inference + lower memory
- Verify CUDA availability before loading

---

## Step 7: Build and Test

### Build the image:
```bash
docker build -t qwen-image-edit:latest .
```

### Test locally (requires GPU):
```bash
docker run --gpus all -p 8080:8080 qwen-image-edit:latest
```

### Verify it works:
```bash
curl http://localhost:8080/health-check
```

---

## Key Concepts Recap

1. **Layer Caching**: Copy dependencies before code to optimize rebuilds
2. **Base Image Selection**: Match your compute requirements (GPU/CPU)
3. **Security**: Always run as non-root user
4. **Environment Variables**: Control Python and pip behavior
5. **Port Configuration**: Use platform-expected ports (often 8080)
6. **Model Loading**: Initialize once at startup, not per-request
7. **Health Checks**: Required for orchestration platforms

---

## Common Pitfalls to Avoid

❌ Copying code before installing dependencies (slower rebuilds)
❌ Running as root user (security vulnerability)
❌ Loading model on every request (extremely slow)
❌ Forgetting to expose the correct port
❌ Not enabling GPU access (`--gpus all`)
❌ Buffered Python output (can't see logs in real-time)

---

## Next Steps

To adapt this for your model:

1. **Choose base image** based on your framework (PyTorch/TensorFlow/JAX)
2. **Update requirements.txt** with your model's dependencies
3. **Modify ModelService** to load your specific model
4. **Update API endpoints** to match your input/output format
5. **Test locally** with sample requests
6. **Deploy** to your platform

---

## Platform Integration Notes

Most ML platforms expect:
- Container listens on port `8080`
- Health check endpoint at `/health-check`
- Non-root user (UID 10000 is common)
- GPU support via `nvidia-docker` runtime
- Logs written to stdout/stderr

This Dockerfile template follows these conventions and should work with minimal modifications.
