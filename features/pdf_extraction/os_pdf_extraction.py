from PIL import Image
import io
import pymupdf
from services.s3 import S3FileManager

from datetime import datetime

import logging

logging.basicConfig(
    filename="output.log",  # File name where logs will be saved
    level=logging.DEBUG,  # Log level (DEBUG logs everything)
    format="%(message)s",  # Only log the message
)
logger = logging.getLogger()


# from services.s3 import S3FileManager
# AWS_BUCKET_NAME = "pdfparserdataset"

def pdf_os_converter(pdf_stream, base_path, s3_obj):
    doc = pymupdf.open(stream=pdf_stream, filetype="pdf")
    md_content = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Extract text and headings
        text = page.get_text("dict")
        for block in text["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["size"] > 12:  # Assuming headings have larger font size
                            md_content.append(f"## {span['text']}\n\n")
                        else:
                            md_content.append(f"{span['text']}\n\n")
        
        # Extract images
        for img_index, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_s3_path = f"images/page{page_num+1}_img{img_index}.{image_ext}"
            
            s3_obj.upload_file(s3_obj.bucket_name, f"{s3_obj.base_path}/{image_s3_path}", image_bytes)

            md_content.append(f"![Image](https://{s3_obj.bucket_name}.s3.amazonaws.com/{s3_obj.base_path}/{image_s3_path})\n\n")
        
        # Extract links
        links = page.get_links()
        for link in links:
            if "uri" in link:
                md_content.append(f"[Link]({link['uri']})\n\n")
        
        # Extract tables
        tables = page.find_tables()
        try:
            for table in tables:
                for row in table.extract():
                    md_content.append(" | ".join(row) + "\n")
                md_content.append("\n")
        except Exception as e:
            print(f"Error processing Tables: {e}")
        
        # Join all markdown content
    final_md_content = "".join(md_content)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    md_file_name = f"{s3_obj.base_path}/extracted_{timestamp}.md"

    s3_obj.upload_file(s3_obj.bucket_name, md_file_name ,final_md_content.encode('utf-8'))
    return md_file_name, final_md_content