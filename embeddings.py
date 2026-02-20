import requests
from typing import List
from config import get_ollama_config


def get_embedding(text: str) -> List[float]:
    cfg = get_ollama_config()
    response = requests.post(
        f"{cfg['base_url']}/api/embeddings",
        json={"model": cfg["embedding_model"], "prompt": text}
    )
    if response.status_code != 200:
        raise Exception(f"Error de Ollama: {response.text}")
    return response.json()["embedding"]


def get_embeddings_batch(texts: List[str], show_progress: bool = True) -> List[List[float]]:
    embeddings = []
    total = len(texts)

    for i, text in enumerate(texts):
        if show_progress and (i + 1) % 100 == 0:
            print(f"Procesando embeddings: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

        if not text or str(text).strip() == "" or str(text).lower() == "none":
            text = "sin información"

        embedding = get_embedding(str(text))
        embeddings.append(embedding)

    return embeddings


def test_ollama_connection() -> bool:
    cfg = get_ollama_config()
    try:
        response = requests.get(f"{cfg['base_url']}/api/tags")
        if response.status_code != 200:
            print("Error: Ollama no está corriendo")
            return False

        models = [m["name"] for m in response.json().get("models", [])]
        model_name = cfg["embedding_model"]
        model_found = any(model_name in m for m in models)

        if not model_found:
            print(f"Modelo '{model_name}' no encontrado. Disponibles: {models}")
            print(f"\nPara instalar: ollama pull {model_name}")
            return False

        test_emb = get_embedding("test")
        print(f"Ollama OK - Modelo: {model_name} - Dimensión embedding: {len(test_emb)}")
        return True

    except requests.exceptions.ConnectionError:
        print("Error: No se puede conectar a Ollama. ¿Está corriendo?")
        print("Inicia Ollama con: ollama serve")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
