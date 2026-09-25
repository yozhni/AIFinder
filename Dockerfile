FROM python:3.11-slim

# HF/container best practice: run as non-root user with UID 1000
RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=0

WORKDIR /home/user/app

# Install dependencies first (better layer caching)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app
COPY --chown=user . .

# Optional: pre-download the embedding model at build time so cold starts
# don't re-fetch all-MiniLM-L6-v2 (~80MB). Uncomment the next line to bake it in.
# RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8080
CMD ["python3", "nicegui_app.py"]
