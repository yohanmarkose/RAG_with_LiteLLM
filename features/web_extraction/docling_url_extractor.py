from pathlib import Path
import io, requests
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc import ImageRefMode
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)
from PIL import Image
from tempfile import NamedTemporaryFile
from docling.datamodel.pipeline_options import PdfPipelineOptions
from services.s3 import S3FileManager
from bs4 import BeautifulSoup
from datetime import datetime
import logging

logging.basicConfig(
    filename="output.log",  # File name where logs will be saved
    level=logging.DEBUG,  # Log level (DEBUG logs everything)
    format="%(message)s",  # Only log the message
)
logger = logging.getLogger()

AWS_BUCKET_NAME = "pdfparserdataset"


def url_docling_converter(web_stream, base_url, base_path, s3_obj):

    # Prepare pipeline options
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    # Initialize the DocumentConverter
    doc_converter = DocumentConverter(
        allowed_formats=[InputFormat.HTML],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            ),
        },
    )
    
    web_stream.seek(0)
    with NamedTemporaryFile(suffix=".html", delete=True) as temp_file:
        # Write the PDF bytes to a temporary file
        temp_file.write(web_stream.read())
        temp_file.flush()
        print(Path(temp_file.name))
        
        # Convert the PDF file to markdown
        # timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # md_file_name = f"{s3_obj.base_path}/extracted_{timestamp}.md"
        md_file_name = f"{s3_obj.base_path}/extracted_data.md"
        conv_result = doc_converter.convert(temp_file.name)
        final_md_content = conv_result.document.export_to_markdown(image_mode=ImageRefMode.REFERENCED)
        temp_file.seek(0)
        
        soup = BeautifulSoup(temp_file.read(), "html.parser")
        #print(soup.prettify('utf-8'))
        for img_tag in soup.find_all("img"):
            img_url = img_tag.get("src")
            if img_url:
                # Handle relative URLs
                if not img_url.startswith("http"):
                    img_url = requests.compat.urljoin(base_url, img_url)
                if '<!-- image -->' in final_md_content:
                    final_md_content = final_md_content.replace(
                        '<!-- image -->', f"\n![image]({img_url})\n", 1
                    )
                else:
                    final_md_content = final_md_content + f"\n![image]({img_url})\n"
                #print(img_url)
                
    # Upload the markdown file to S3   
    s3_obj.upload_file(s3_obj.bucket_name, md_file_name ,final_md_content.encode('utf-8'))
        
    # Return the markdown file name and content
    return md_file_name, final_md_content


