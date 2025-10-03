import httpx
import json
import time

print("Testing Ollama speed...")
start = time.time()

payload = {
    'model': 'qwen3:latest',
    'prompt': 'Hello, write one sentence.',
    'stream': False
}

try:
    r = httpx.post('http://ollama:11434/api/generate', json=payload, timeout=60.0)
    elapsed = time.time() - start
    result = json.loads(r.text)
    
    print(f"✅ Response: {result.get('response', 'NO RESPONSE')[:100]}")
    print(f"⏱️  Time: {elapsed:.1f} seconds")
    
except httpx.TimeoutException:
    print(f"❌ TIMEOUT after {time.time() - start:.1f} seconds")
except Exception as e:
    print(f"❌ ERROR: {e}")


