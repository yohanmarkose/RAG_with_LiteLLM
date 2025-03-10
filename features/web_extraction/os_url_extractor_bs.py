import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from datetime import datetime

def clean_text(text):
    """Remove extra whitespace and clean up text"""
    return re.sub(r'\s+', ' ', text).strip()

def scrape_to_markdown(url):
    md_content = []

    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Removing unwanted elements
    for tag in soup.find_all(['script', 'style']):
        tag.decompose()

    md_content.append(f"Source: {url}\n\n")

    main_content = soup.find('main') or soup.find('body')
    
    # Finding the necessary data (headings, images content and tables)
    for element in main_content.find_all(['h1', 'h2', 'p', 'img', 'table'], recursive=True):
        if element.name == 'h1':
            md_content.append(f"# {clean_text(element.text)}\n\n")
            
        elif element.name == 'h2':
            md_content.append(f"## {clean_text(element.text)}\n\n")
            
        elif element.name == 'p':
            text = clean_text(element.text)
            if text:
                md_content.append(f"{text}\n\n")

        elif element.name == 'img':
            src = element.get('src', '')
            if src:
                # Handling relative URLs
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(url, src)
                alt = element.get('alt', 'image')
                md_content.append(f"![{alt}]({src})\n\n")
                
        elif element.name == 'table':
            # Process table headers
            headers = []
            for th in element.find_all('th'):
                headers.append(clean_text(th.text))
            
            if headers:
                md_content.append('| ' + ' | '.join(headers) + ' |\n')
                md_content.append('| ' + ' | '.join(['---'] * len(headers)) + ' |\n')
            
            # Process table rows
            for row in element.find_all('tr'):
                cols = []
                for td in row.find_all('td'):
                    cols.append(clean_text(td.text))
                if cols:  # Only write non-empty rows
                    md_content.append('| ' + ' | '.join(cols) + ' |\n')
            md_content.append('\n')

    return "".join(md_content)