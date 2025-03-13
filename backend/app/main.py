from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Body
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from litellm import completion

from io import BytesIO
import os
from dotenv import load_dotenv
import re
from datetime import datetime
import base64

# Docling imports
import requests
from bs4 import BeautifulSoup

from redis import Redis
import redis
import uuid, time, json

from features.pdf_extraction.docling_pdf_extractor import pdf_docling_converter
from features.web_extraction.docling_url_extractor import url_docling_converter

# from services import s3
from services.s3 import S3FileManager

load_dotenv()

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
# DIFFTBOT_API_TOKEN = os.getenv("DIFFBOT_API_TOKEN") 
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Models Configuration (from environment variable or default)
SUPPORTED_MODELS = os.getenv("SUPPORTED_MODELS", "gpt-4o,gemini-1.5-pro").split(",")


app = FastAPI()

# Redis client setup
# redis_client = Redis(host=os.getenv('REDIS_HOST', 'redis'), port=int(os.getenv('REDIS_PORT', 6379)))
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Stream name in Redis
REQUEST_STREAM_NAME = "request_stream"
RESPONSE_STREAM_NAME = "response_stream"
REQUEST_CONSUMER_GROUP = "request_group"
RESPONSE_CONSUMER_GROUP = "request_group"
REQUEST_CONSUMER_NAME = "Worker"
RESPONSE_CONSUMER_NAME = "Response_Worker"

class URLInput(BaseModel):
    url: str

class PdfInput(BaseModel):
    file: str
    file_name: str
    model: str

class S3FileListResponse(BaseModel):
    files: List[str]

class SelectPdfResponse(BaseModel):
    selected_file: str

class SummarizeRequest(BaseModel):
    selected_file: str
    model: str
class QuestionRequest(BaseModel):
    question: str
    selected_file: str
    model: str

@app.get("/")
def read_root():
    return {"message": "Document Chat API: FastAPI Backend with Redis and LiteLLM is running"}

@app.get("/list_pdfcontent", response_model=S3FileListResponse)
def get_available_files():
    base_path = base_path = f"pdf/docling/"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    files = list({file.split('/')[-2] for file in s3_obj.list_files()})
    return {"files": files}

@app.post("/select_pdfcontent")
def get_selected_pdf(request: SelectPdfResponse):
    base_path = base_path = f"pdf/docling/"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    file = f"{base_path}{request.selected_file}/extracted_data.md"
    content = s3_obj.load_s3_file_content(file)
    return {"content": content}

@app.post("/summarize")
def summarize_content(request: SummarizeRequest):
    try:
        content = request.selected_file
        if not content:
            raise HTTPException(status_code=400, detail="No content found in selected files")
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes document content."},
            {"role": "user", "content": f"Summarize the following document content in one sentence:\n\n{content}"}
        ]
                
        print(request.model)
        summary = generate_model_response(request.model, messages)
        
        return {
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.post("/ask_question")
def ask_question(request: QuestionRequest):
    try:
        content = request.selected_file
        
        if not content:
            raise HTTPException(status_code=400, detail="No content found in selected files")
        
        # Prepare messages for LLM
        system_message = """You are a helpful assistant. Please respond based on the following document:
{context}
If the question isn't related to the provided documents, politely inform the user that you can only answer questions about the selected documents.""".format(context=content)
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": request.question}
        ]
        
        answer = generate_model_response(request.model, messages) 
        
        return {
            "answer": answer,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")

# PDF Docling 
@app.post("/upload_pdf")
def process_pdf_docling(uploaded_pdf: PdfInput):
    pdf_content = base64.b64decode(uploaded_pdf.file)
    # Convert pdf_content to a BytesIO stream for pymupdf
    pdf_stream = BytesIO(pdf_content)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    # base_path = f"pdf/docling/{uploaded_pdf.file_name.replace('.','').replace(' ','')}_{timestamp}/"
    base_path = f"pdf/docling/{uploaded_pdf.file_name.replace('.','').replace(' ','')}/"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/{uploaded_pdf.file_name}", pdf_content)
    file_name, result = pdf_docling_converter(pdf_stream, base_path, s3_obj)
    return {
        "message": f"Data Scraped and stored in S3 \n Click the link to Download: https://{s3_obj.bucket_name}.s3.amazonaws.com/{file_name}",
        "scraped_content": result  # Include the original scraped content in the response
    }
    

# Web Docling  
@app.post("/scrape-url-docling")
def process_docling_url(url_input: URLInput):
    response = requests.get(url_input.url)
    soup = BeautifulSoup(response.content, "html.parser")
    html_content = soup.encode("utf-8")
    html_stream = BytesIO(html_content)
    
    # Setting the S3 bucket path and filename
    html_title = f"URL_{soup.title.string}.txt"
    print(html_title)
    base_path = f"web/docling/{html_title.replace('.','').replace(' ','').replace(',','').replace("’","").replace('+','')}/"

    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/{html_title}", BytesIO(url_input.url.encode('utf-8')))
    file_name, result = url_docling_converter(html_stream, url_input.url, base_path, s3_obj)

    return {
        "message": f"Data Scraped and stored in S3 \n Click the link to Download: https://{s3_obj.bucket_name}.s3.amazonaws.com/{file_name}",
        "scraped_content": result  # Include the original scraped content in the response
    }
    
def get_pdf_content(request: QuestionRequest):
    base_path = base_path = f"pdf/docling/"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    file = f"{base_path}{request.selected_file}/extracted_data.md"
    content = s3_obj.load_s3_file_content(file)
    return content

def generate_model_response(model, messages):
    # response = completion(
    #     model=model,
    #     messages=messages
    # )
    request_data = {
        "id": str(uuid.uuid4()),  # Generate a unique request ID
        "model": model,  # Replace with an available model for LiteLLM
        "prompt": messages
    }
    
    response = redis_communication(request_data)
    
    return response

def redis_communication(request_data):
    # Push request to Redis queue
    # redis_client.rpush("request_queue", json.dumps(request_data))
    print("Pushing request to Redis Stream")
    
    # Serialize nested data (if any) before passing to Redis
    for key, value in request_data.items():
        if isinstance(value, (dict, list)):
            request_data[key] = json.dumps(value)  # Convert dict/list to a JSON string
        
    redis_client.xadd(REQUEST_STREAM_NAME, request_data)
    
    print(f"Request {request_data['id']} pushed to Redis Stream!")

    # Poll Redis for the response
    response_key = f"response:{request_data['id']}"
    timeout = 30  # Maximum wait time in seconds
    start_time = time.time()

    print("Waiting for response...")

    while time.time() - start_time < timeout:

        response_data = redis_client.xreadgroup(
            RESPONSE_CONSUMER_GROUP, RESPONSE_CONSUMER_NAME, {RESPONSE_STREAM_NAME: ">"}, count=1, block=0
        )
        
        if response_data:
            # print(response_data)
            for stream_name, message_data in response_data:
                print(stream_name)
                for message_id, data in message_data:
                    if data['id'] == request_data['id']:
                        # print(data['response'])
                        response = json.loads(data['response'])
                        redis_client.xack(RESPONSE_STREAM_NAME, RESPONSE_CONSUMER_GROUP, message_id)
                        print("Response received successfully")
                        # Extract message content safely
                        if "choices" in response and isinstance(response["choices"], list):
                            message_content = response["choices"][0].get("message", {}).get("content", "No content found")
                            print(f"Generated Response: {message_content}")
                            return message_content
                        else:
                            print("Error: 'choices' field missing or invalid format in response")
                
        # if response:
        #     # response = json.loads(response)
        #     response = json.loads(response[0][1][0][1])
        #     if response["id"] == request_data["id"]:
        #         # Extract message content safely
        #         if "choices" in response and isinstance(response["choices"], list):
        #             message_content = response["choices"][0].get("message", {}).get("content", "No content found")
        #             print(f"Generated Response: {message_content}")
        #             return message_content
        #         else:
        #             print("Error: 'choices' field missing or invalid format in response")
            
        #     break  # Exit loop once response is received
        

    # if not response:
    #     return("Timeout: No response received within the specified time.")
    
    return "response.choices[0].message.content"