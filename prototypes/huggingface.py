import os
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

if not HUGGINGFACE_API_KEY:
    raise ValueError("HUGGINGFACE_API_KEY not found in .env file")

response = completion(
    model="huggingface/Qwen/Qwen2.5-Coder-32B-Instruct",
    messages=[{"content": "Hello, how are you?", "role": "user"}],
    stream=True,
    api_key=HUGGINGFACE_API_KEY
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
