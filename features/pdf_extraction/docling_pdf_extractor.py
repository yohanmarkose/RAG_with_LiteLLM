from pathlib import Path
import io
from docling.document_converter import DocumentConverter
from pydantic import BaseModel
from docling.datamodel.base_models import InputFormat, DocumentStream
from docling_core.types.doc import ImageRefMode, PictureItem
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)
from tempfile import NamedTemporaryFile
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from services.s3 import S3FileManager

from datetime import datetime
import logging

logging.basicConfig(
    filename="output.log",  # File name where logs will be saved
    level=logging.DEBUG,  # Log level (DEBUG logs everything)
    format="%(message)s",  # Only log the message
)
logger = logging.getLogger()

AWS_BUCKET_NAME = "pdfparserdataset"

def pdf_docling_converter(pdf_stream: io.BytesIO, base_path, s3_obj):

    # Prepare pipeline options
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    # Initialize the DocumentConverter
    doc_converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            ),
        },
    )
    
    pdf_stream.seek(0)
    with NamedTemporaryFile(suffix=".pdf", delete=True) as temp_file:
        # Write the PDF bytes to a temporary file
        temp_file.write(pdf_stream.read())
        temp_file.flush()
        print(Path(temp_file.name))
        # Convert the PDF file to markdown
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # md_file_name = f"{s3_obj.base_path}/extracted_{timestamp}.md"
        md_file_name = f"{s3_obj.base_path}/extracted_data.md"
        # doc_stream = DocumentStream({"name": md_file_name, "stream": pdf_stream})
        conv_result = doc_converter.convert(temp_file.name)
        
        final_md_content = document_convert(conv_result, base_path, s3_obj)

        # Upload the markdown file to S3   
        s3_obj.upload_file(s3_obj.bucket_name, md_file_name ,final_md_content.encode('utf-8'))
        
    # Return the markdown file name and content
    return md_file_name, final_md_content

def document_convert(conv_result, base_path, s3_obj):
    final_md_content = conv_result.document.export_to_markdown(image_mode=ImageRefMode.PLACEHOLDER)
    doc_filename = conv_result.input.file.stem

    picture_counter = 0
    for element, _level in conv_result.document.iterate_items():
        if isinstance(element, PictureItem):
            picture_counter += 1
            
            # Save the image to a file
            element_image_filename = f"{s3_obj.base_path}/images/{doc_filename}_image_{picture_counter}.png"

            # Upload the image file to S3   
            # image_data = 

            # with element_image_filename.open("wb") as fp:
            #     element.get_image(conv_result.document).save(fp, "PNG")
            
            with NamedTemporaryFile(suffix=".png", delete=True) as image_file:
                #image_file.write(image_data)
                element.get_image(conv_result.document).save(image_file, "PNG")
                image_file.flush()
                                
                # Upload the image file to S3   
                with open(image_file.name, "rb") as fp:
                    s3_obj.upload_file(s3_obj.bucket_name, element_image_filename, fp.read())
                    
                # s3_obj.upload_file(s3_obj.bucket_name, element_image_filename, image_file)
                
                element_image_link = f"https://{s3_obj.bucket_name}.s3.amazonaws.com/{f"{element_image_filename}"}"
            
                print(element_image_link)
                
            # Replace the image placeholder with the image filename
            final_md_content = final_md_content.replace("<!-- image -->", f"![Image]({element_image_link})", 1)
            

    return final_md_content
