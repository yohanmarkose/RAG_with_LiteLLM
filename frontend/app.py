import time
import streamlit as st
import requests, os, base64

from litellm import completion
from io import StringIO

API_URL = "http://backend:8000"


if "page" not in st.session_state:
    st.session_state.page = "Document Parser"
if "text_url" not in st.session_state:
    st.session_state.text_url = ""
if "file_upload" not in st.session_state:
    st.session_state.file_upload = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_files" not in st.session_state:
    st.session_state.selected_files = ""

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
        st.session_state.text_url = st.text_input("Enter URL here")
        convert = st.button("Process", use_container_width=True)
    elif input_format == "PDF":
        st.session_state.text_url = ""         
        st.session_state.file_upload = st.file_uploader("Choose a PDF File", type="pdf", accept_multiple_files=False)    
        convert = st.button("Process", use_container_width=True)
        
    # Define what happens on each page
    if convert:
        if input_format == "WebURL":
            if st.session_state.text_url:
                if check_url(st.session_state.text_url):
                    st.success(f"The URL '{st.session_state.text_url}' exists and is accessible!")
                    convert_web_to_markdown(st.session_state.text_url)
                else:
                    st.error(f"The URL '{st.session_state.text_url}' does not exist or is not accessible.")
            else:
                st.info("Please enter a URL.")
    
        elif input_format == "PDF":
            if st.session_state.file_upload:
                st.success(f"File '{st.session_state.file_upload.name}' uploaded successfully!")
                convert_PDF_to_markdown(st.session_state.file_upload)
            else:
                st.info("Please upload a PDF file.")
            
def chat_page():
    st.title("Chat with Documents")

    # Get available files from API
    try:
        response = requests.get(f"{API_URL}/select_pdfcontent")
        if response.status_code == 200:
            available_files = response.json()["files"]
        else:
            st.error("Error fetching available files")
            available_files = []
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        available_files = []
    
    model_options = {
        "OpenAI": "gpt-4o-mini",
        "Anthropic": "claude-2",
        "HuggingFace": "huggingface/facebook/blenderbot-400M-distill"
    }

    # Model selection dropdown
    selected_model = st.sidebar.selectbox("Choose LLM", options=list(model_options.keys()))
    model_name = model_options[selected_model]
    
    # File selection
    st.session_state.selected_files = st.sidebar.selectbox(
        "Select PDF for Context",
        options=available_files,
    )
    
    if not st.session_state.selected_files:
        st.info("Please select a pdf from the sidebar to start chatting.")
        return
    
    # Summarize button
    if st.sidebar.button("Summarize"):
        with st.spinner("Generating summary..."):
            try:
                response = requests.post(
                    f"{API_URL}/summarize",
                    json={
                        "selected_files": st.session_state.selected_files,
                        "model": model_name
                    }
                )
                if response.status_code == 200:
                    summary = response.json()["summary"]
                    st.markdown("### Summary")
                    st.markdown(summary)
                else:
                    st.error(f"Error generating summary: {response.text}")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
    
    # Reset chat button
    if st.sidebar.button("New Chat"):
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the documents..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_URL}/ask_question",
                        json={
                            "question": prompt,
                            "selected_files": st.session_state.selected_files,
                            "model": model_name
                        }
                    )
                    
                    if response.status_code == 200:
                        answer = response.json()["answer"]
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        error_message = f"Error: {response.text}"
                        st.error(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
                except Exception as e:
                    error_message = f"Error: {str(e)}"
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

def convert_web_to_markdown(text_url):
    progress_bar = st.progress(0)  
    progress_text = st.empty()  
    
    progress_text.text("Starting conversion...")
    progress_bar.progress(25)

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
        
def convert_PDF_to_markdown(file_upload):    
    progress_bar = st.progress(0)
    progress_text = st.empty()
    
    progress_text.text("Uploading file...")
    progress_bar.progress(20)

    if file_upload is not None:
        bytes_data = file_upload.read()
        base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
        
        progress_text.text("Sending file for processing...")
        progress_bar.progress(50)

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
        page_title="Document Parser",
        layout="wide",
        initial_sidebar_state="expanded"
    )    
    main()