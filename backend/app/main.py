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

from features.pdf_extraction.docling_pdf_extractor import pdf_docling_converter
from features.web_extraction.docling_url_extractor import url_docling_converter
from features.pdf_extraction.docling_pdf_extractor import pdf_docling_converter
from features.web_extraction.docling_url_extractor import url_docling_converter

# from services import s3
from services.s3 import S3FileManager

load_dotenv()
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
# DIFFTBOT_API_TOKEN = os.getenv("DIFFBOT_API_TOKEN") 
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

app = FastAPI()
class URLInput(BaseModel):
    url: str

class PdfInput(BaseModel):
    file: str
    file_name: str
    model: str

class S3FileListResponse(BaseModel):
    files: List[str]

class SummarizeRequest(BaseModel):
    selected_files: str
    model: str
class QuestionRequest(BaseModel):
    question: str
    selected_files: List[str]
    model: str

@app.get("/")
def read_root():
    return {"message": "Document Chat API is running"}

@app.get("/select_pdfcontent", response_model=S3FileListResponse)
def get_available_files():
    base_path = base_path = f"pdf/docling/"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    files = list({file.split('/')[-2] for file in s3_obj.list_files()})
    return {"files": files}

@app.post("/summarize")
def summarize_content(request: SummarizeRequest):
    try:
        # Get content from selected files
        base_path = base_path = f"pdf/docling/"
        s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
        file = f"{base_path}{request.selected_files}/extracted_data.md"
        content = s3_obj.load_s3_file_content(file)

        if not content:
            raise HTTPException(status_code=400, detail="No content found in selected files")

        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes document content."},
            {"role": "user", "content": f"Summarize the following document content in one sentence:\n\n{content}"}
        ]
        
        # Use litellm or equivalent for model-agnostic API calls
        response = completion(
            model=request.model,
            messages=messages
        )
        
        summary = response.choices[0].message.content
        
        return {
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

# @app.post("/ask_question")
# def ask_question(request: QuestionRequest):
#     """Answer a question based on the content of selected files"""
#     try:
#         # Get content from selected files
#         base_path = base_path = f"pdf/os/"
#         s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
#         context_content = ""
#         for file in request.selected_files:
#             content = load_s3_file_content(file)
#             context_content += f"\n\n# {file}\n{content}"
        
#         if not context_content:
#             raise HTTPException(status_code=400, detail="No content found in selected files")
        
#         # Prepare messages for LLM
#         system_message = """You are a helpful assistant. Please respond based on the following documents:

# {context}

# If the question isn't related to the provided documents, politely inform the user that you can only answer questions about the selected documents.""".format(context=context_content)
        
#         messages = [
#             {"role": "system", "content": system_message},
#             {"role": "user", "content": request.question}
#         ]
        
#         # Use litellm or equivalent for model-agnostic API calls
#         from litellm import completion
        
#         response = completion(
#             model=request.model,
#             messages=messages
#         )
        
#         answer = response.choices[0].message.content
        
#         return {
#             "answer": answer,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")

# PDF Docling 
@app.post("/scrape_pdf_docling")
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
    
# To get url domain name from url
def url_to_folder_name(url):
    # Extract the main domain
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        domain = match.group(1).replace("www.", "")
    else:
        return None
    safe_folder_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", domain)
    return safe_folder_name