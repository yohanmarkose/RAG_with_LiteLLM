import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.title("Web Scraper and PDF Processor")

# URL Scraping
st.header("Scrape a Web URL")
url = st.text_input("Enter the URL:")
if st.button("Scrape URL"):
    if url:
        # Make a POST request to the FastAPI endpoint
        response = requests.post(f"{API_URL}/scrape-url", json={"url": url})
        
        if response.status_code == 200:
            # Extract the response data
            data = response.json()
            st.success(data["message"])
            
            # Display the scraped content
            st.subheader("Scraped Content")
            st.text_area("Content", data["scraped_content"], height=300)  # Show the scraped text
        else:
            st.error("An error occurred while scraping the URL.")
    else:
        st.error("Please enter a valid URL.")

# PDF Upload
st.header("Process a PDF File")
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
if st.button("Process PDF"):
    if uploaded_file:
        files = {"file": uploaded_file.getvalue()}
        response = requests.post(f"{API_URL}/process-pdf", files={"file": uploaded_file})
        st.success(response.json()["message"])
    else:
        st.error("Please upload a valid PDF")