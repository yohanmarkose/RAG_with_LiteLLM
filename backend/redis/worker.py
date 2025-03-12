import redis
import json
import time
import litellm
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def process_requests():
    while True:
        
        _, request_data = redis_client.blpop("request_queue")
        
        request = json.loads(request_data)
        
        request_id = request["id"]
        model = request["model"]
        prompt = request["prompt"]
        
        try:
            # Generate response using LiteLLM
            response = litellm.completion(
                model=model,
                # messages=[{"role": "user", "content": prompt}],
                messages=prompt,
                # max_tokens=max_tokens,
            )
            
            print(json.dumps(response.model_dump(), indent=2))
            print(response.choices[0].message.content)
            
            # Store response in Redis
            redis_client.set(f"response:{request_id}", json.dumps(response.model_dump(), indent=2), ex=3600)
            print(f"Generated response for {request_id} successfully")
        except Exception as e:
            error_response = {"error": str(e)}
            redis_client.set(f"response:{request_id}", json.dumps(error_response), ex=3600)
            print(f"Error processing request {request_id}: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    print("Worker started, waiting for tasks...")
    process_requests()