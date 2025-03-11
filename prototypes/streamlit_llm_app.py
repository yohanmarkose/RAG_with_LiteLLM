import streamlit as st
from litellm import completion
import os

# Set API keys
HUGGINGFACE_API_KEY = os.environ["HUGGINGFACE_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Model selection dropdown
model_options = {
    "HuggingFace": "huggingface/facebook/blenderbot-400M-distill",
    "OpenAI": "gpt-4o-mini",
    "Anthropic": "claude-2" 
}

selected_model = st.selectbox("Choose LLM", options=list(model_options.keys()))

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Your message:"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
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
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})