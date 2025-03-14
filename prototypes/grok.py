import os
from litellm import completion

XAI_API_KEY = os.getenv("XAI_API_KEY")

response = completion(
    model="xai/grok-2-latest",
    messages=[
        {"role": "user", "content": "What's the weather like in Boston today in Fahrenheit?"}
    ],
    api_key=XAI_API_KEY  # Ensure the key is passed
)

print(response)
