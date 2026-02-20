import os
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "collections.yaml")
SECRETS_PATH = os.path.join(os.path.dirname(__file__), "collections.secrets.yaml")


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _is_named_dict_list(value):
    return isinstance(value, list) and all(isinstance(i, dict) and "name" in i for i in value)


def _merge_values(base, override):
    if override is None:
        return base
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = _merge_values(merged[key], value)
            else:
                merged[key] = value
        return merged
    if isinstance(base, list) and isinstance(override, list):
        if _is_named_dict_list(base) and _is_named_dict_list(override):
            merged = [dict(item) for item in base]
            index = {item["name"]: i for i, item in enumerate(merged)}
            for item in override:
                name = item["name"]
                if name in index:
                    merged[index[name]] = _merge_values(merged[index[name]], item)
                else:
                    merged.append(item)
            return merged
        return override
    return override


def _load_config():
    config = _load_yaml(CONFIG_PATH)
    if os.path.isfile(SECRETS_PATH):
        secrets = _load_yaml(SECRETS_PATH)
        config = _merge_values(config, secrets)
    return config


def get_ollama_config():
    return _load_config()["ollama"]


def get_chroma_config():
    return _load_config()["chroma"]


def list_collections():
    return list(_load_config().get("collections", {}).keys())


def get_collection_config(name):
    collections = _load_config().get("collections", {})
    if name not in collections:
        available = ", ".join(collections.keys()) or "(ninguna)"
        raise ValueError(f"Colección '{name}' no encontrada. Disponibles: {available}")
    return collections[name]
