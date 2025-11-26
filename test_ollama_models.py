"""Quick test to verify Ollama connectivity and models."""

import requests
import json

print("Checking Ollama API...")

# Check available models
try:
    response = requests.get("http://localhost:11434/api/tags")
    models = response.json()
    print(f"\n✓ API accessible")
    print(f"Available models: {len(models.get('models', []))}")
    for model in models.get("models", []):
        print(f"  - {model['name']}")
except Exception as e:
    print(f"❌ API error: {e}")
    exit(1)

# Try Mistral
print("\nTesting Mistral...")
try:
    payload = {
        "model": "mistral",
        "prompt": "Describe a fortress under siege in one sentence.",
        "stream": False,
    }
    response = requests.post(
        "http://localhost:11434/api/generate", json=payload, timeout=30
    )
    if response.status_code == 200:
        result = response.json()
        resp_text = result.get("response", "")
        print(f"✓ Mistral works! Response: {resp_text[:100]}...")
    else:
        print(f"❌ Status {response.status_code}")
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")

# Try Phi
print("\nTesting Phi-3...")
try:
    payload = {"model": "phi", "prompt": "What is a fortress?", "stream": False}
    response = requests.post(
        "http://localhost:11434/api/generate", json=payload, timeout=30
    )
    if response.status_code == 200:
        result = response.json()
        resp_text = result.get("response", "")
        print(f"✓ Phi works! Response length: {len(resp_text)}")
    else:
        print(f"❌ Status {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nDone!")
