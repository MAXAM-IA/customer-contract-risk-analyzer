from functools import lru_cache
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
import os
import streamlit as st
from azure.storage.blob import BlobServiceClient, ContentSettings
import mimetypes
from azure.identity import DefaultAzureCredential
import vertexai
import requests
from google.cloud import storage
from langchain_google_vertexai import ChatVertexAI
import base64
from langchain_google_genai import ChatGoogleGenerativeAI
import httpx

# -*- coding: utf-8 -*-
"""
LLM API for Azure and GCP
This module provides functions to interact with LLMs hosted on Azure and GCP.
It includes functions to invoke basic and vision chains, upload files to Azure Blob Storage and GCP, and handle streaming responses.
"""

#@st.cache_resource
@lru_cache()
def get_llm(provider="gcp"):
    if provider == "gcp":
        
        
        LLM_MODEL = "gemini-2.5-flash-preview-05-20"
        llm = ChatGoogleGenerativeAI(
            #model="gemini-2.0-flash",
            model=LLM_MODEL,
            temperature=0,
            max_tokens=None,
            #timeout=None,
            max_retries=2,
            http_client=httpx.Client(verify=False)
            # other params...
        )
        return llm
    else:
        azure_endpoint = str(os.getenv("APP_SERVICE_NLP_API_URL", "")).rstrip("/")
        api_key = os.getenv("APP_SERVICE_NLP_API_KEY", "")

        azure_endpoint = "https://openai-cc-risk.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2025-01-01-preview"
        return AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        azure_deployment="gpt-4o-mini",  # or your deployment
        api_version="2024-08-01-preview",  # or your api version
        temperature=0
    )

def create_chain_basic_call():

    llm = get_llm()
    prompt_objetivo_basic = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Responde a la pregunta del usuario
                """,
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ]
    )

    chain_objetivo_basic = prompt_objetivo_basic | llm | StrOutputParser()
    return chain_objetivo_basic

def invoke_basic_chain(input_text, chat_history, streaming=True):
    with st.spinner("Generando respuesta..."):
        #llm = get_llm(provider="gcp")
        chain_objetivo_basic = create_chain_basic_call()
        if streaming:
            res = ""
            for chunk in chain_objetivo_basic.stream({"input": input_text,
                                                "chat_history": chat_history}):
                res += chunk
                yield chunk
            invoke_basic_chain.response = res
        else:
            res = chain_objetivo_basic.invoke({"input": input_text})
            return res

# Función para obtener MIME type
def get_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"

CONTAINER_NAME = "ccriskcontainer"


storage_client = storage.Client(project="ai-cc-risk-analyzer-storage")
bucket_name = 'cc-risk-analyzer-bucket'
bucket = storage_client.bucket(bucket_name)

def create_vision_chain(uploaded_files):
    llm = get_llm()
    messages = [
    (
        "system",
        "Responde a la pregunta del usuario en español.",
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ]
    file_data_list = []
    for uploaded_file in uploaded_files:

        file_data = base64.b64encode(uploaded_file.read()).decode("utf-8")
        file_data_list.append(file_data)
        print("Fichero leído:", uploaded_file.name)
        #print("file_data", file_data)
        #print("file_bytes", file_bytes)

        print("Tipo de fichero:", uploaded_file.type)
        print("Tamaño del fichero:", uploaded_file.size, "bytes")

        messages.append(
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
        print("Fichero añadido a los mensajes:", uploaded_file.name)

    prompt_objetivo = ChatPromptTemplate.from_messages(
    messages=messages
        )

    chain_objetivo = prompt_objetivo | llm | StrOutputParser()

    return chain_objetivo, file_data_list

def invoke_vision_chain(input_text, chat_history, uploaded_files, streaming=True):
    with st.spinner("Leyendo fichero..."):
        chain_objetivo, file_data_list = create_vision_chain(uploaded_files=uploaded_files)
    with st.spinner("Generando respuesta..."):
        if streaming:
            res = ""
            print("chat_history",chat_history)
            for chunk in chain_objetivo.stream({"input": input_text,
                                                "chat_history": chat_history}):
                res += chunk
                yield chunk
            invoke_vision_chain.files = file_data_list
            invoke_vision_chain.response = res
        else:
            res = chain_objetivo.invoke({"input": input_text})
            return res