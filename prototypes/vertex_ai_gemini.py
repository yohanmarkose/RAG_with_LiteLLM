from litellm import completion
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up Vertex AI credentials and configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "GOOGLE_APPLICATION_CREDENTIALS.json"
os.environ["VERTEX_PROJECT"] = "vertexai-llm-453423"
os.environ["VERTEX_LOCATION"] = "us-central1"

def process_query(query_text, image_url=None, max_tokens=300):
    """
    Process a query with optional image input using Vertex AI's Gemini model.
    
    Args:
        query_text (str): The text query to process
        image_url (str, optional): URL to an image to include in the query
        max_tokens (int, optional): Maximum number of tokens in the response
        
    Returns:
        The model's response
    """
    # Select the appropriate model
    model = "vertex_ai/gemini-1.5-pro"
    
    # Prepare the message content
    if image_url:
        # If image URL is provided, create a multimodal message
        content = [
            {"type": "text", "text": query_text},
            {"type": "image_url", "image_url": image_url}
        ]
    else:
        # Text-only query
        content = query_text
    
    # Create the messages array based on whether we have an image or not
    if image_url:
        messages = [{"role": "user", "content": content}]
    else:
        messages = [{"role": "user", "content": content}]
    
    # Make the API call
    response = completion(
        model=model,
        messages=messages,
        max_tokens=max_tokens
    )
    
    return response

# Example usage - text only
text_response = process_query("Hello, how are you?")
print("Text-only response:")
print(text_response.choices[0].message.content)
print("\nResponse cost:", text_response._hidden_params["response_cost"])

# Example usage - text with image
image_response = process_query(
    "Please summarize the given image in less than 30 words.",
    "https://pdfparserdataset.s3.us-east-2.amazonaws.com/pdf/os/170603762v7pdf_2025-02-25_18-16-54/images/page3_img1.png"
)
print("\nText+Image response:")
print(image_response.choices[0].message.content)
print("\nResponse cost:", image_response._hidden_params["response_cost"])