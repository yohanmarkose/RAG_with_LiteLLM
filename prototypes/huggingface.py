import os
from dotenv import load_dotenv
from litellm import completion
import litellm

load_dotenv()

# litellm.success_callback=["supabase"]
# litellm.failure_callback=["supabase"]

### SUPABASE
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_URL")

litellm.success_callback = ["athina"]

ATHINA_API_KEY = os.getenv("ATHINA_API_KEY")

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

if not HUGGINGFACE_API_KEY:
    raise ValueError("HUGGINGFACE_API_KEY not found in .env file")

response = completion(
    model="huggingface/Qwen/Qwen2.5-Coder-32B-Instruct",
    messages=[{"content": "What the weather like today in Boston?", "role": "user"}],
    stream=True,
    api_key=HUGGINGFACE_API_KEY,
    metadata={
    "environment": "staging",
    "prompt_slug": "my_prompt_slug/v1"
  }
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
