import redis
import json
import time
import litellm
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Stream name in Redis
REQUEST_STREAM_NAME = "request_stream"
RESPONSE_STREAM_NAME = "response_stream"
REQUEST_CONSUMER_GROUP = "request_group"
RESPONSE_CONSUMER_GROUP = "request_group"
REQUEST_CONSUMER_NAME = "Worker"
RESPONSE_CONSUMER_NAME = "Response_Worker"


# Create a consumer group if it doesn't exist (only need to be run once)
try:
    redis_client.xgroup_create(REQUEST_STREAM_NAME, REQUEST_CONSUMER_GROUP, id="0", mkstream=True)
except redis.exceptions.ResponseError:
    # Consumer group already exists
    pass


# Create a consumer group for the response stream if it doesn't exist (only need to be run once)
try:
    redis_client.xgroup_create(RESPONSE_STREAM_NAME, RESPONSE_CONSUMER_GROUP, id="0", mkstream=True)
except redis.exceptions.ResponseError:
    # Consumer group already exists
    pass

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def process_requests():
    while True:
        
        request_data = redis_client.xreadgroup(
            REQUEST_CONSUMER_GROUP, REQUEST_CONSUMER_NAME, {REQUEST_STREAM_NAME: ">"}, count=1, block=0
        )
        for stream_name, message_data in request_data:
            for message_id, data in message_data:
                
                try:
                    print(stream_name, message_id)
                    redis_client.xack(REQUEST_STREAM_NAME, REQUEST_CONSUMER_GROUP, message_id)
                    request = data
                    request_id = request["id"]
                    model = request["model"]
                    prompt = json.loads(request["prompt"])

                    response = litellm.completion(
                        model=model,
                        messages=prompt,
                    )
                    
                    # Prepare the response data to be added to the response stream
                    response_data = {
                        "id": request_id,
                        "response": json.dumps(response.model_dump(), indent=2),  # Serialize the response to JSON
                    }
                    
                    print(f"Generated response for {request_id} successfully")
                    
                    # Push the response to the response stream
                    redis_client.xadd(RESPONSE_STREAM_NAME, response_data)
                    print(f"Pushed response for {request_id} to the response stream.")
                    
                except Exception as e:
                    print(f"Error processing message {message_id}: {e}")
        time.sleep(1)

if __name__ == "__main__":
    print("Worker started, waiting for tasks...")
    process_requests()