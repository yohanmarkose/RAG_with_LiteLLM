from fastapi import FastAPI
from pydantic import BaseModel

# Models for request/response
class PDFUploadRequest(BaseModel):
    file: str
    file_name: str
    tool: str
    model: Optional[str] = ""

class WebURLRequest(BaseModel):
    url: str
    tool: str

class QuestionRequest(BaseModel):
    question: str
    selected_files: List[str]
    model: str

class SummarizeRequest(BaseModel):
    selected_files: List[str]
    model: str

class S3FileListResponse(BaseModel):
    files: List[str]