from diagrams import Diagram, Cluster
from diagrams.custom import Custom
from diagrams.aws.storage import S3
from diagrams.gcp.compute import Run
from diagrams.onprem.client import User
from diagrams.programming.framework import FastAPI
from diagrams.digitalocean.compute import Docker
from diagrams.onprem.inmemory import Redis

# Create the diagram
with Diagram("PDF Insight Application Architecture", show=False, filename="diagram", direction="LR"):
    # User interaction
    user = User("User")
    
    # Input Mechanism Cluster
    with Cluster("User Input"):
        pdf_input = Custom("PDF File Upload", "./src/pdf.png")  # Replace with an appropriate local or online icon for PDF upload
    
    # Streamlit Frontend Cluster (Generic Node)
    with Cluster("Frontend (Streamlit)"):
        frontend = Custom("Streamlit UI", "./src/streamlit.png")  # Use a custom icon for Streamlit
    
    # Cloud Services
    cloud_run = Run("Google Cloud Run")
    
    # Storage
    s3_storage = S3("Amazon S3")

    # Backend Cluster
    with Cluster("Backend (FastAPI)"):
        # Docker Image for Backend Services
        docker_image = Docker("Docker Image") 
        backend = FastAPI("FastAPI Service")
        docling = Custom("Docling Tool", "./src/docling.png")
        litellm = Custom("Litellm", "./src/litellm.png")

        
    with Cluster("REDIS In-Memory Cache"):
        redis_req = Redis("Request Stream")
        redis_res = Redis("Response Stream")

    with Cluster("LiteLLM Logging and Analysis"):
        athina = Custom("Athina AI", "./src/athina.png")
    
    # Connections
    user >> pdf_input >> frontend >> backend# User provides input via URL or PDF upload to Streamlit UI
    cloud_run >> docker_image >> backend  # Google Cloud Run runs the Docker image containing backend services
    backend >> docling  # Backend uses selected processing tools
    docling >> s3_storage  # Processed data is saved to Amazon S3
    s3_storage >> backend  # Backend retrieves processed data from Amazon S3
    backend >> redis_req >> litellm >> redis_res >> backend # Backend uses Redis to manage request and response streams for LLM feedback
    backend >> frontend  # Backend sends messages to the frontend for user feedback
    litellm >> athina  # LLM sends processed data to Athina AI for logging and analysis