"""Vector embedding generation using sentence-transformers."""

from sentence_transformers import SentenceTransformer

# Load model once (global cache)
_model = None

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def get_model():
    """Get or load the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def generate_embedding(text):
    """Generate a single embedding vector from text."""
    model = get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def batch_embed(texts):
    """Generate embeddings for a list of texts."""
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    return embeddings.tolist()


def build_embedding_text(product):
    """Build text for embedding from product fields."""
    parts = []
    for field in ["product_name", "brand", "category", "application",
                  "use_case", "specifications", "used_for", "requires",
                  "alternative_to", "typical_user_question"]:
        value = product.get(field, "")
        if value:
            parts.append(str(value))
    return " ".join(parts)
