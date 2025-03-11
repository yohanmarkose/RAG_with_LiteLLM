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
from datetime import datetime

# Docling imports
import requests
from bs4 import BeautifulSoup

from features.pdf_extraction.docling_pdf_extractor import pdf_docling_converter
from features.web_extraction.docling_url_extractor import url_docling_converter
from features.pdf_extraction.os_pdf_extraction import pdf_os_converter
from features.pdf_extraction.docling_pdf_extractor import pdf_docling_converter
from features.web_extraction.docling_url_extractor import url_docling_converter

# OS we extraction imports
from features.web_extraction import os_url_extractor_bs

#Diffbot imports

# from features.web_extraction.diffbot_python_client.diffbot_client import DiffbotClient,DiffbotCrawl,DiffbotSpecificExtraction

# import pprint
# import time
# import ast

# Aure AI imports
# from features.pdf_extraction.azure_ai_intelligent_doc.read_azure_ai_model import read_azure_ai_model

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
    
@app.get("/")
def read_root():
    return {"message": "Document Chat API is running"}

@app.get("/select_pdfcontent", response_model=S3FileListResponse)
def get_available_files():
    base_path = base_path = f"pdf/os/"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    files = list({file.split('/')[-2] for file in s3_obj.list_files()})
    return {"files": files}

@app.post("/summarize")
def summarize_content(request: SummarizeRequest):
    try:
        # Get content from selected files
        base_path = base_path = f"pdf/os/"
        s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
        context_content = ""
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

@app.post("/scrape_url_os_bs")
def process_url(url_input: URLInput):
    md_result = os_url_extractor_bs.scrape_to_markdown(url_input.url)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    folder_name = url_to_folder_name(url_input.url)
    # base_path = f"web/os/{folder_name}_{timestamp}/"
    # base_path = f"web/os/{folder_name}/"
    base_path = f"web/os/{folder_name}/"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/web_url.txt", str(url_input.url))

    # md_result = convert_json_to_markdown(json_result) # Scrape the URL
    s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/extracted_data.md", str(md_result))

    return {
        "message": f"Data Scraped and stored S3 \n Click the link to Download: https://{s3_obj.bucket_name}.s3.amazonaws.com/{s3_obj.base_path}/extracted_data.md",
        "scraped_content": md_result
    }

# OS PDF - Pymupdf
@app.post("/scrape_pdf_os")
def process_pdf_os(uploaded_pdf: PdfInput):
    pdf_content = base64.b64decode(uploaded_pdf.file)
    # Convert pdf_content to a BytesIO stream for pymupdf
    pdf_stream = BytesIO(pdf_content)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    # base_path = f"pdf/os/{uploaded_pdf.file_name.replace('.','').replace(' ','')}_{timestamp}/"
    base_path = f"pdf/os/{uploaded_pdf.file_name.replace('.','').replace(' ','')}/"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/{uploaded_pdf.file_name}", pdf_content)
    file_name, result = pdf_os_converter(pdf_stream, base_path, s3_obj)
    return {
        "message": f"Data Scraped and stored in S3 \n Click the link to Download: https://{s3_obj.bucket_name}.s3.amazonaws.com/{file_name}",
        "scraped_content": result
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
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    print(html_title)
    # base_path = f"web/docling/{html_title.replace('.','').replace(' ','').replace(',','').replace("’","").replace('+','')}_{timestamp}/"
    base_path = f"web/docling/{html_title.replace('.','').replace(' ','').replace(',','').replace("’","").replace('+','')}/"

    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/{html_title}", BytesIO(url_input.url.encode('utf-8')))
    file_name, result = url_docling_converter(html_stream, url_input.url, base_path, s3_obj)
    print(base_path)
    print(file_name)
    return {
        "message": f"Data Scraped and stored S3 \n Click the link to Download: https://{s3_obj.bucket_name}.s3.amazonaws.com/{file_name}",
        "scraped_content": result  # Include the original scraped content in the response
    }
    

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
        "message": f"Data Scraped and stored S3 \n Click the link to Download: https://{s3_obj.bucket_name}.s3.amazonaws.com/{file_name}",
        "scraped_content": result  # Include the original scraped content in the response
    }

# @app.post("/scrape_diffbot_en_url")
# def diffbot_process_url(url_input: URLInput):
#     diffbot = DiffbotClient()
#     token = DIFFTBOT_API_TOKEN
#     url = url_input.url
#     api = "analyze"
#     response = diffbot.request(url, token , api, fields=['title', 'text', 'images', 'pageUrl', 'type'])
#     if isinstance(response, str):
#         try:
#             response = ast.literal_eval(response)
#         except Exception as e:
#             print(f"Error converting response: {e}")
#         exit()
#     objects = response.get("objects", [])
#     extracted_data = extract_for_markdownrender(objects)
#     # Generate Markdown content
#     markdown_content = f"# Diffbot Extracted Content\n\n" 
#     markdown_content += f"**Date:** {datetime.now().strftime('%A, %B %d, %Y, %I:%M %p %Z')}\n\n"
#     for item in extracted_data:
#         markdown_content += f"### Title : \n{item['title']}\n"
#         markdown_content += f"### Page URL\n[{item['pageUrl']}]({item['pageUrl']})\n"
#         markdown_content += f"### Identified Page Type\n[{item['type']}]({item['type']})\n"
#         markdown_content += f"### Text Extracts \n{item['text']}\n"
#         markdown_content += f"### Images Extracts \n"
#         if 'images' in item and isinstance(item['images'], list):
#             for image in item['images']:
#                 image_url = image['url']
#                 image_title = image['title']
#                 markdown_content += f"{image_title} : ![{image_title}]({image_url})\n\n"
#         else:
#             markdown_content += f"## Images Extracts : \n No Images Found\n"
#     #file_name = "diffbot_scraped_url.md"

#     timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
#     folder_name = url_to_folder_name(url_input.url)
#     base_path = f"web/ent/{folder_name}_{timestamp}/"
#     s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
#     s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/diffbot_scraped_url.txt", str(url_input.url))
#     s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/extracted_data.md", str(markdown_content))

#     return {
#         "message": f"Data Scraped and stored in https://{s3_obj.bucket_name}.s3.amazonaws.com/{base_path}extracted_data.md",
#         "scraped_content": markdown_content  
#     }


@app.post("/azure-intdoc-process-pdf")
async def azure_int_doc_process_pdf(uploaded_pdf: PdfInput):
    try :
        pdf_content = base64.b64decode(uploaded_pdf.file)
        pdf_stream = BytesIO(pdf_content)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        base_path = f"pdf/ent/{uploaded_pdf.file_name.replace('.', '').replace(' ','')}_{timestamp}/"
        s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
        s3_obj.upload_file(AWS_BUCKET_NAME, f"{s3_obj.base_path}/{uploaded_pdf.file_name}", pdf_content)
        result = read_azure_ai_model(pdf_stream,uploaded_pdf.model)        
        try:
            result = read_azure_ai_model(pdf_stream, uploaded_pdf.model)
            if not result:
                raise ValueError("Azure AI Model returned an empty response")
            
        except Exception as azure_error:
            return {
                "message": f"Error analyzing document: {str(azure_error)}.",
                "scraped_content": "Refer to azure documentation for the file size requirement."
            }
        # Ensure extracted data is valid before uploading
        extracted_data_path = f"{s3_obj.base_path}/{uploaded_pdf.model}/extracted_data.md"
        if isinstance(result, str) and result.strip():
            s3_obj.upload_file(AWS_BUCKET_NAME, extracted_data_path, result)
        else:
            return {
                "message": "Extracted data is empty or invalid",
                "scraped_content": result
            }
        
        return {
            "message": f"Data Scraped and stored in https://{s3_obj.bucket_name}.s3.amazonaws.com/{base_path}{uploaded_pdf.model}/extracted_data.md",
            "scraped_content": result
        }
    except Exception as e:
        return {"error": f"Unexpected error processing PDF: {str(e)}"}
    
    
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

def extract_for_markdownrender(data):
    extracted_data = []
    for obj in data:
        title = obj.get("title", "No Title Found")
        page_url = obj.get("pageUrl", "No URL Found")
        type = obj.get("type", "No Type Found")
        text = obj.get("text", "No Text Found")
        images = obj.get("images", [])

        # Extract image titles and URLs
        image_data = []
        if isinstance(images, list):
            for image in images:
                image_url = image.get("url", "No URL Found")
                image_title = image.get("title", "No Title Found")
                image_data.append({"url": image_url, "title": image_title})

        extracted_data.append({
            "title": title,
            "pageUrl": page_url,
            "type": type,
            "text": text,
            "images": image_data
        })
    return extracted_data