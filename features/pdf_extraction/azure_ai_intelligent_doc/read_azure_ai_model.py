import os
import io
from tempfile import NamedTemporaryFile
from fastapi import UploadFile
from azure.core.exceptions import HttpResponseError
from dotenv import find_dotenv, load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature, AnalyzeResult, AnalyzeDocumentRequest

load_dotenv()

def get_words(page, line):
    result = []
    for word in page.words:
        if _in_span(word, line.spans):
            result.append(word)
    return result

def _in_span(word, spans):
    for span in spans:
        if word.span.offset >= span.offset and (word.span.offset + word.span.length) <= (span.offset + span.length):
            return True
    return False

# how to obtain the endpoint and check .env file for key
endpoint = os.getenv("DOCUMENTINTELLIGENCE_ENDPOINT")
key = os.getenv("DOCUMENTINTELLIGENCE_API_KEY")

if not endpoint or not key:
    raise EnvironmentError("Azure environment variables are not set.")

def analyze_read(input_pdf):
    
    document_intelligence_client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    with open(input_pdf, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-read",
            body=f,
            features=[DocumentAnalysisFeature.LANGUAGES],
            content_type="application/octet-stream",
        )
    result: AnalyzeResult = poller.result()

    markdown_content = "## Document Read Analysis Results\n"

    # Text content
    markdown_content += "### Text Content:\n\n"      
    if result.paragraphs is not None:
        for paragraph in result.paragraphs:
            markdown_content += f"{paragraph.content}\n\n"
    else:
        markdown_content += "No paragraphs found.\n\n"

    # Pages Details
    markdown_content += "### Pages:\n\n"
    for page in result.pages:
        markdown_content += f"**Page number**: {page.page_number}\n**Width**: {page.width}\n**Height**: {page.height}\n**Unit**: {page.unit}\n"
        if result.languages is not None:
            for language in result.languages:
                markdown_content += f"**Language code**: '{language.locale}' with confidence {language.confidence}\n"
        markdown_content += "\n"

    return markdown_content

def analyze_layout(input_pdf_path):
    if not input_pdf_path or not os.path.exists(input_pdf_path):
        raise ValueError("Invalid input PDF path")

    document_intelligence_client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    with open(input_pdf_path, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout", 
            body=f, 
            content_type="application/octet-stream"
        )
    
    result: AnalyzeResult = poller.result()

    markdown_content = "# Document Layout Analysis Results\n\n"
    
    # Handwritten Content Check
    markdown_content += "## Handwritten Content:\n\n"
    if result.styles and any([style.is_handwritten for style in result.styles]):
        markdown_content += "Document contains handwritten content\n\n"
    else:
        markdown_content += "Document does not contain handwritten content\n\n"

    # Pages Details
    markdown_content += "### Pages:\n\n"
    for page in result.pages:
        markdown_content += f"### Page #{page.page_number}\n"
        markdown_content += f"Page has width: {page.width} and height: {page.height}, measured with unit: {page.unit}\n\n"
        page_words = []
        if page.lines:
            for line in page.lines:
                words = get_words(page, line)
                for word in words:
                    page_words.append(word.content)
        if page_words:
            markdown_content += "**Text from the page:**\n"
            markdown_content += " ".join(page_words) + "\n\n"
        if hasattr(page, 'spans') and page.spans is not None:
            for span in page.spans:
                markdown_content += f"**Span**: {span}\n"
        markdown_content += "\n"

    # Tables
    markdown_content += "## Tables\n\n"
    if result.tables:
        for table_idx, table in enumerate(result.tables):
            markdown_content += f"Table #{table_idx + 1}: {table.row_count} rows x {table.column_count} columns\n"
            for cell in table.cells:
                markdown_content += f"- Cell[{cell.row_index}, {cell.column_index}]: {cell.content}\n"
            markdown_content += "\n"
    else:
        markdown_content += "No tables found in the document.\n\n"

    # Figures
    markdown_content += "## Figures\n\n"
    if result.figures:
        for figure_idx, figure in enumerate(result.figures):
            markdown_content += f"Figure # {figure_idx + 1} has the following spans: {figure.spans}\n"
            markdown_content += f"Figure #{figure_idx + 1}: Found on page {figure.bounding_regions[0].page_number}\n"
            markdown_content += "\n"
            for region in figure.bounding_regions:
                markdown_content += f"Within bounding polygon '{region.polygon}'\n"
    else:
        markdown_content += "No figures found in the document.\n\n"

    return markdown_content

def read_azure_ai_model(pdf_stream: io.BytesIO,model):
    from azure.core.exceptions import HttpResponseError
    pdf_stream.seek(0)
    with NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_stream.read())
        temp_pdf.flush()
        try:
        # Use the model parameter to determine which model to use
            if model == "read":
            # Call the analyze_read function
                markdown_content = analyze_read(temp_pdf.name)
            elif model == "layout":
            # Call the analyze_layout function
                markdown_content = analyze_layout(temp_pdf.name)
            else:
                raise ValueError("Invalid model specified")
            
            return markdown_content
        except HttpResponseError as e:
            print(f"Error analyzing document: {e}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
        return None