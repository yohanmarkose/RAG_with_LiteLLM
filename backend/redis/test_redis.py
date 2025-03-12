import redis
import json
import uuid
import time

# Initialize Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Sample request payload
request_data = {
    "id": str(uuid.uuid4()),  # Generate a unique request ID
    "model": "gemini/gemini-1.5-pro",  # Replace with an available model for LiteLLM
    "prompt": "What is the capital of USA?"
}

# Push request to Redis queue
redis_client.rpush("request_queue", json.dumps(request_data))

print(f"Sample request {request_data['id']} pushed to Redis!")

# Poll Redis for the response
response_key = f"response:{request_data['id']}"
timeout = 30  # Maximum wait time in seconds
start_time = time.time()

print("Waiting for response...")

while time.time() - start_time < timeout:
    response = redis_client.get(response_key)
    
    if response:
        response = json.loads(response)
        # print(f"Response received:\n{json.dumps(response, indent=2)}")
        
        # response = json.dumps(response, indent=2)
        # Extract message content safely
        if "choices" in response and isinstance(response["choices"], list):
            message_content = response["choices"][0].get("message", {}).get("content", "No content found")
            print(f"Generated Response: {message_content}")
        else:
            print("Error: 'choices' field missing or invalid format in response")
        
        break  # Exit loop once response is received
    
    time.sleep(1)  # Wait before checking again

if not response:
    print("Timeout: No response received within the specified time.")

