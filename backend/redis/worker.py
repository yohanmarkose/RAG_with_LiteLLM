import redis
import json
import time
import litellm
from dotenv import load_dotenv
import os

load_dotenv()

litellm.success_callback = ["athina"]


# Initialize Redis client
# redis_client = redis.Redis(host="redis-18117.c261.us-east-1-4.ec2.redns.redis-cloud.com", port=18117)

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    decode_responses=True,
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
)

# Stream name in Redis
REQUEST_STREAM_NAME = os.getenv("REQUEST_STREAM_NAME")
RESPONSE_STREAM_NAME = os.getenv("RESPONSE_STREAM_NAME")
REQUEST_CONSUMER_GROUP = os.getenv("REQUEST_CONSUMER_GROUP")
RESPONSE_CONSUMER_GROUP = os.getenv("RESPONSE_CONSUMER_GROUP")
REQUEST_CONSUMER_NAME = os.getenv("REQUEST_CONSUMER_NAME")
RESPONSE_CONSUMER_NAME = os.getenv("RESPONSE_CONSUMER_NAME")


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
ATHINA_API_KEY = os.environ["ATHINA_API_KEY"]
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
                        messages=prompt
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