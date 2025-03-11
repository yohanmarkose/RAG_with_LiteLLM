import time
import streamlit as st
import requests, os, base64

import boto3
from litellm import completion
from io import StringIO

API_URL = "http://127.0.0.1:8000"


if "page" not in st.session_state:
    st.session_state.page = "Document Parser"
if "text_url" not in st.session_state:
    st.session_state.text_url = ""
if "file_upload" not in st.session_state:
    st.session_state.file_upload = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# S3 configuration
S3_BUCKET_NAME = "mdcontents"  # Replace with your bucket name

def get_s3_client():
    return boto3.client('s3')

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_markdown_files():
    try:
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME)
        files = [item['Key'] for item in response.get('Contents', []) if item['Key'].endswith('.md')]
        return files
    except Exception as e:
        st.error(f"Error accessing S3 bucket: {e}")
        return []

# Load markdown file content from S3
def load_markdown_content(file_key):
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=file_key)
        content = response['Body'].read().decode('utf-8')
        return content
    except Exception as e:
        st.error(f"Error loading file {file_key}: {e}")
        return ""
    


def main():
    # Set up navigation
    st.sidebar.header("Main Menu")
    page = st.sidebar.radio("Choose a page:", ["Document Parser", "Chat with Documents"])
    st.session_state.page = page
    
    if page == "Document Parser":
        document_parser_page()
    elif page == "Chat with Documents":
        chat_page()

def document_parser_page():
    # Set the title of the app
    st.title("Markdown Chat - LLM")
    # Add a sidebar
    st.sidebar.header("Main Menu")
    input_format = st.sidebar.selectbox("Choose a format:", ["WebURL", "PDF"])
    
    if "text_url" not in st.session_state:
        st.session_state.text_url = ""
    if "file_upload" not in st.session_state:
        st.session_state.file_upload = None

    if input_format == "WebURL":
        st.session_state.file_upload = None
        tool = st.sidebar.selectbox("Choose a method to convert URL:", 
                                    ["BeautifulSoup (OS)", "Diffbot (Enterprise)", "Docling"])
        st.session_state.text_url = st.text_input("Enter URL here")
        convert = st.button("Process", use_container_width=True)
    elif input_format == "PDF":
        st.session_state.text_url = ""
        tool = st.sidebar.selectbox("Choose a method to convert PDF:", 
                                    ["PyMuPDF (OS)", "Azure Document Intelligence (Enterprise)", "Docling"])           
        if tool == "Azure Document Intelligence (Enterprise)":
            radio = st.radio("Choose a model :", ["Read", "Layout"])
        else:
            radio = None
        st.session_state.file_upload = st.file_uploader("Choose a PDF File", type="pdf", accept_multiple_files=False)    
        convert = st.button("Process", use_container_width=True)
        
    # Define what happens on each page
    if convert:
        if input_format == "WebURL":
            if st.session_state.text_url:
                if check_url(st.session_state.text_url):
                    st.success(f"The URL '{st.session_state.text_url}' exists and is accessible!")
                    convert_web_to_markdown(tool, st.session_state.text_url)
                else:
                    st.error(f"The URL '{st.session_state.text_url}' does not exist or is not accessible.")
            else:
                st.info("Please enter a URL.")
    
        elif input_format == "PDF":
            if st.session_state.file_upload:
                st.success(f"File '{st.session_state.file_upload.name}' uploaded successfully!")
                convert_PDF_to_markdown(tool, st.session_state.file_upload, radio)
            else:
                st.info("Please upload a PDF file.")
            
def chat_page():
    st.title("Chat with Documents")
    
    # Model selection dropdown
    model_options = {
        "OpenAI": "gpt-4o-mini",
        "Anthropic": "claude-2",
        "HuggingFace": "huggingface/facebook/blenderbot-400M-distill"
    }
    
    # Sidebar for configuration
    selected_model = st.sidebar.selectbox("Choose LLM", options=list(model_options.keys()))
    
    # Get markdown files and allow user to select
    markdown_files = get_markdown_files()
    selected_files = st.sidebar.multiselect(
        "Select Markdown Files for Context",
        options=markdown_files,
        default=markdown_files[:1] if markdown_files else []
    )
    
    # Load selected markdown content
    context_content = ""
    if selected_files:
        for file in selected_files:
            content = load_markdown_content(file)
            context_content += f"\n\n# {file}\n{content}"
        
        # Show a preview of the context
        with st.sidebar.expander("Context Preview"):
            st.markdown(context_content[:500] + "..." if len(context_content) > 500 else context_content)
    else:
        st.info("Please select at least one document from the sidebar to start chatting.")
        return
    
    # Prepare system message with context
    system_message = """You are a helpful assistant. Please respond based on the following documents:

{context}

If the question isn't related to the provided documents, politely inform the user that you can only answer questions about the selected documents.""".format(context=context_content)
    
    # Reset chat button
    if st.sidebar.button("Reset Chat"):
        st.session_state.messages = []
    
    # Initialize chat messages if needed
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "system", "content": system_message}]
    elif st.session_state.messages[0]["role"] == "system":
        # Update system message if context changes
        st.session_state.messages[0]["content"] = system_message
    else:
        # Insert system message if not present
        st.session_state.messages.insert(0, {"role": "system", "content": system_message})
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] != "system":  # Don't show system messages
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the documents..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            try:
                response = completion(
                    model=model_options[selected_model],
                    messages=st.session_state.messages,
                    stream=True
                )
                
                full_response = ""
                placeholder = st.empty()
                for chunk in response:
                    full_response += chunk.choices[0].delta.content or ""
                    placeholder.markdown(full_response + "▌")
                
                placeholder.markdown(full_response)
                
                # Add assistant response to messages
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                error_message = f"Error generating response: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})


def check_url(url):
    try:
        response = requests.head(url, timeout=5)  # Send HEAD request
        if response.status_code == 200:
            return True
        return False
    except requests.RequestException:
        return False

def convert_web_to_markdown(tool, text_url):
    progress_bar = st.progress(0)  
    progress_text = st.empty()  
    
    progress_text.text("Starting conversion...")
    progress_bar.progress(25)

    if tool == "BeautifulSoup (OS)":
        response = requests.post(f"{API_URL}/scrape_url_os_bs", json={"url": text_url})
    elif tool == "Diffbot (Enterprise)":
        response = requests.post(f"{API_URL}/scrape_diffbot_en_url", json={"url": text_url})
    elif tool == "Docling":
        response = requests.post(f"{API_URL}/scrape-url-docling", json={"url": text_url})
    
    progress_text.text("Processing request...")
    progress_bar.progress(50)
    
    try:
        if response.status_code == 200:
            data = response.json()
            progress_text.text("Finalizing output...")
            progress_bar.progress(75)
            st.subheader(data["message"])
            st.markdown(data["scraped_content"], unsafe_allow_html=True)
        else:
            st.error("Server not responding.")
    except:
        st.error("An error occurred while processing the url")
    
    progress_bar.progress(100)
    progress_text.empty()
    progress_bar.empty()
        
def convert_PDF_to_markdown(tool, file_upload, radio):    
    progress_bar = st.progress(0)
    progress_text = st.empty()
    
    progress_text.text("Uploading file...")
    progress_bar.progress(20)

    if file_upload is not None:
        bytes_data = file_upload.read()
        base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
        
        progress_text.text("Sending file for processing...")
        progress_bar.progress(50)
        
        if tool == "PyMuPDF (OS)":
            response = requests.post(f"{API_URL}/scrape_pdf_os", json={"file": base64_pdf, "file_name": file_upload.name, "model": ""})
        elif tool == "Azure Document Intelligence (Enterprise)":
            model = "read" if radio == "Read" else "layout"
            response = requests.post(f"{API_URL}/azure-intdoc-process-pdf", json={"file": base64_pdf, "file_name": file_upload.name, "model": model})
        elif tool == "Docling":
            response = requests.post(f"{API_URL}/scrape_pdf_docling", json={"file": base64_pdf, "file_name": file_upload.name, "model": ""})
        
        progress_text.text("Processing document...")
        progress_bar.progress(75)
        
        try:
            if response.status_code == 200:
                data = response.json()
                progress_text.text("Finalizing output...")
                st.subheader(data["message"])
                st.markdown(data["scraped_content"], unsafe_allow_html=True)
            else:
                st.error("Server not responding.")
        except:
            st.error("An error occurred while processing the PDF.")
    
    progress_bar.progress(100)
    progress_text.empty()
    progress_bar.empty()        
    
if __name__ == "__main__":
# Set page configuration
    st.set_page_config(
        page_title="Document Parser",  # Name of the app
        layout="wide",              # Layout: "centered" or "wide"
        initial_sidebar_state="expanded"  # Sidebar: "expanded" or "collapsed"
    )    
    main()