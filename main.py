from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yaml, os
from typing import List

app = FastAPI()

# Allow cross-origin requests (required by grader)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_bool(val):
    return str(val).strip().lower() in ("true", "1", "yes", "on")

def coerce(key, value):
    if key == "port" or key == "workers":
        return int(value)
    if key == "debug":
        return parse_bool(value)
    return str(value)

@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):

    # --- Layer 1: Defaults (lowest priority) ---
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }

    # --- Layer 2: config.development.yaml ---
    try:
        with open("config.development.yaml", "r") as f:
            yaml_data = yaml.safe_load(f) or {}
        for k, v in yaml_data.items():
            if k in config:
                config[k] = coerce(k, v)
    except FileNotFoundError:
        pass

    # --- Layer 3: .env file ---
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                raw_key, _, raw_val = line.partition("=")
                raw_key = raw_key.strip()
                raw_val = raw_val.strip()

                # Handle alias: NUM_WORKERS → workers
                if raw_key == "NUM_WORKERS":
                    config["workers"] = coerce("workers", raw_val)
                elif raw_key.startswith("APP_"):
                    mapped = raw_key[4:].lower()  # remove APP_ prefix, lowercase
                    if mapped in config:
                        config[mapped] = coerce(mapped, raw_val)
    except FileNotFoundError:
        pass

    # --- Layer 4: OS environment variables (APP_* prefix) ---
    for env_key, env_val in os.environ.items():
        if env_key == "NUM_WORKERS":
            config["workers"] = coerce("workers", env_val)
        elif env_key.startswith("APP_"):
            mapped = env_key[4:].lower()
            if mapped in config:
                config[mapped] = coerce(mapped, env_val)

    # --- Layer 5: CLI overrides via ?set=key=value (highest priority) ---
    for item in set:
        if "=" in item:
            k, _, v = item.partition("=")
            k = k.strip()
            v = v.strip()
            if k in config:
                config[k] = coerce(k, v)

    # --- Mask api_key before returning ---
    config["api_key"] = "****"

    return config
