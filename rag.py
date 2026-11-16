import os
import re
import json
import numpy as np
import requests
import streamlit as st
from dotenv import load_dotenv

EMBED_MODEL = "embeddinggemma"
CHAT_MODEL = "qwen3:4b"
PINGGY_HEADERS = {"X-Pinggy-No-Screen": "true"}


def _get_ollama_url() -> str:
    """Reloads .env and returns a normalized Ollama base URL without trailing slash."""
    load_dotenv(override=True)
    url = os.getenv("OLLAMA_URL", "").strip().strip('"').strip("'").rstrip("/")
    if not url:
        raise requests.exceptions.ConnectionError(
            "OLLAMA_URL is missing in .env. Please set your Ollama/Pinggy URL."
        )
    return url


def get_embedding(text: str) -> list[float]:
    """Calls Ollama's embeddinggemma model via HTTP to embed a text string."""
    base_url = _get_ollama_url()
    resp = requests.post(
        f"{base_url}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        headers=PINGGY_HEADERS,
        timeout=90,
    )
    if not resp.ok:
        raise requests.exceptions.HTTPError(
            f"HTTP {resp.status_code} from Ollama ({base_url}/api/embeddings): {resp.text}"
        )
    data = resp.json()
    if "embedding" in data:
        return data["embedding"]
    if "embeddings" in data and data["embeddings"]:
        return data["embeddings"][0]
    raise ValueError("Unexpected embedding response format from Ollama server.")


@st.cache_resource(show_spinner="Embedding travel guide with embeddinggemma (runs once)...")
def load_and_embed_kb(filepath: str = "knowledge_base.json") -> list[dict]:
    """Loads the JSON travel guide and embeds all entries ONCE per server session."""
    with open(filepath, "r", encoding="utf-8") as f:
        kb = json.load(f)
    for entry in kb:
        # Combine title and text so both place names and details are captured in the vector
        combined_text = f"{entry['title']}: {entry['text']}"
        entry["embedding"] = np.array(get_embedding(combined_text), dtype=np.float32)
    return kb


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Computes cosine similarity between two 1D numpy vectors."""
    denom = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)


def retrieve_top_k(
    question: str,
    kb: list[dict],
    k: int = 3,
    category: str | None = None,
) -> list[dict]:
    """
    Retrieves the top-k most relevant guide entries using the
    Filter -> Score -> Top-k pattern:
      1. Filter: keep valid entries (and match optional category if provided).
      2. Score: compute cosine similarity between question embedding and entry embedding.
      3. Top-k: sort descending by score and return top k entries.
    """
    q_vec = np.array(get_embedding(question), dtype=np.float32)

    # 1. Filter candidates
    candidates = [
        entry
        for entry in kb
        if entry.get("text") and (category is None or entry.get("category") == category)
    ]

    # 2. Score candidates by cosine similarity
    scored = []
    for entry in candidates:
        score = cosine_similarity(q_vec, entry["embedding"])
        clean_entry = {key: val for key, val in entry.items() if key != "embedding"}
        clean_entry["score"] = score
        scored.append(clean_entry)

    # 3. Sort descending and select top-k
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]


def _strip_thinking_tags(text: str) -> str:
    """Removes <think>...</think> reasoning blocks returned by Qwen3 models."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "</think>" in cleaned:
        cleaned = cleaned.split("</think>")[-1]
    cleaned = cleaned.strip()
    return cleaned if cleaned else text.strip()


def generate_answer(
    question: str,
    retrieved_entries: list[dict],
    min_score: float = 0.35,
) -> str:
    """
    Generates an answer using qwen3:4b strictly from the retrieved top-k entries.
    Includes a two-stage 'I don't know' safeguard:
      - Stage 1 (Retrieval threshold): if best cosine similarity < min_score, abstain immediately.
      - Stage 2 (Prompt constraint): instruct qwen3:4b to say 'I don't know' if context lacks the answer.
    """
    if not retrieved_entries or retrieved_entries[0]["score"] < min_score:
        return "I don't know based on the travel guide."

    # Build context block with explicit entry IDs
    context_blocks = [
        f"[{e['id']}] {e['title']}\nText: {e['text']}\nSource: {e['source']}"
        for e in retrieved_entries
    ]
    context_str = "\n\n".join(context_blocks)

    system_prompt = (
        "You are the official travel assistant for Lumen Travel covering Ho Chi Minh City. "
        "You must answer the user's question concisely using ONLY the provided travel guide entries in the Context. "
        "Rules:\n"
        "1. Always cite the entry ID(s) you used in square brackets, such as [G01] or [G03].\n"
        "2. Output ONLY the final answer to the user. Do not output your internal reasoning steps.\n"
        "3. Do NOT invent, assume, or extrapolate opening hours, ticket prices, addresses, or facts not explicitly stated in the Context.\n"
        "4. If the provided Context entries do not contain the specific information needed to answer the question, reply: \"I don't know based on the travel guide.\""
    )
    user_prompt = f"Context:\n{context_str}\n\nQuestion: {question} /no_think"

    base_url = _get_ollama_url()
    resp = requests.post(
        f"{base_url}/api/chat",
        json={
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": False,
            "options": {"temperature": 0.0},
        },
        headers=PINGGY_HEADERS,
        timeout=120,
    )
    if not resp.ok:
        raise requests.exceptions.HTTPError(
            f"HTTP {resp.status_code} from Ollama ({base_url}/api/chat): {resp.text}"
        )
    raw_content = resp.json().get("message", {}).get("content", "")
    return _strip_thinking_tags(raw_content)
