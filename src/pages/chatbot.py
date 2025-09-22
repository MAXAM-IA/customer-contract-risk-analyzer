import streamlit as st
import random
import time
import os, base64

from model.llm_api import invoke_basic_chain, invoke_vision_chain

def render_or_update_model_info(model_name):
    """
    Renders or updates the model information on the webpage.

    Args:
        model_name (str): The name of the model.

    Returns:
        None
    """
    # Leer y aplicar estilos CSS
    css_path = os.path.join(os.path.dirname(__file__), '..', 'design', 'assistant', 'styles.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

    # Codificar imagen como base64
    image_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'maxam-logo-no-background.png')
    with open(image_path, 'rb') as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode()
    image_data_uri = f"data:image/png;base64,{img_base64}"

    # Leer y renderizar HTML con imagen embebida
    html_path = os.path.join(os.path.dirname(__file__), '..', 'design', 'assistant', 'content.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html_template = f.read()
    html = html_template.format(logo=image_data_uri, model=model_name)


    st.markdown(html, unsafe_allow_html=True)

# Reset chat history
def reset_chat_history():
    """
    Resets the chat history by clearing the 'messages' list in the session state.
    """
    if "messages" in st.session_state:
        st.session_state.messages = []

model_options = ["gpt4o-mini"]

# Initialize model
if "model" not in st.session_state:
    st.session_state.model = model_options[0]
    st.session_state.temperature = 0
    st.session_state.messages = []

    
with st.sidebar:
    st.title("Configuración de modelo")

    # Select model
    st.session_state.model = st.selectbox(
        "Elige un modelo:",
        model_options,
        index=0
    )

    # Select temperature
    st.session_state.temperature = st.slider('Selecciona una temperatura:', min_value=0.0, max_value=1.0, step=0.01, format="%.2f")

    # Reset chat history button
    if st.button("Clear Chat 🧹", use_container_width=True):
        reset_chat_history()
    
# Render or update model information
render_or_update_model_info(st.session_state.model)

for message in st.session_state.messages:   
        if type(message[1]) == list:
            for item in message[1]:
                if item["type"] == "file":
                    with st.chat_message(message[0], avatar="📄"):
                        # Display file information
                        with st.status(item['filename']):
                            st.markdown(f"**Nombre:** {item['filename']}")
                            st.markdown(f"**Tipo:** {item['mime_type']}")
                            st.markdown(f"**Tamaño:** {len(item['data'])} bytes")
        else:
            with st.chat_message(message[0]):
                st.markdown(message[1])

# Accept user input
st.session_state.prompt = st.chat_input(
    placeholder="¿En qué puedo ayudarte?",
    accept_file="multiple",
    file_type = ["pdf"]
)
 

if st.session_state.prompt:
    
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(st.session_state.prompt.text)

    if st.session_state.prompt.files:
            for uploaded_file in st.session_state.prompt.files:
                # Display file information
                with st.chat_message("user", avatar="📄"):
                    with st.status(uploaded_file.name):
                        st.markdown(f"**Nombre:** {uploaded_file.name}")
                        st.markdown(f"**Tipo:** {uploaded_file.type}")
                        st.markdown(f"**Tamaño:** {uploaded_file.size} bytes")
                #st.markdown(f"**Tamaño:** {uploaded_file.size} bytes")
                

    with st.chat_message("assistant"):
        if st.session_state.prompt.files:
            
            response = invoke_vision_chain(
                input_text=st.session_state.prompt.text,
                chat_history=st.session_state.messages,
                uploaded_files=st.session_state.prompt.files,
                streaming=True
            )
        else:
            response = invoke_basic_chain(
                input_text=st.session_state.prompt.text,
                chat_history=st.session_state.messages,
                streaming=True
            )
        st.write_stream(response)
        print(st.session_state.prompt.files)
    # Add user message to chat history
    
    if not st.session_state.prompt.files:
        
        st.session_state.messages.append(("user", st.session_state.prompt.text))
        st.session_state.messages.append(("assistant", invoke_basic_chain.response))
    else:
        st.session_state.messages.append(("user", st.session_state.prompt.text))

        for uploaded_file, file_data in zip(st.session_state.prompt.files, invoke_vision_chain.files):
            st.session_state.messages.append(
                (
                "human",
                [
                    {
                        "type": "file",
                        "source_type": "base64",
                        "data": file_data,
                        "mime_type": uploaded_file.type,
                        "filename": uploaded_file.name,
                    }
                ],
            )
            )
        st.session_state.messages.append(("assistant",invoke_vision_chain.response))
