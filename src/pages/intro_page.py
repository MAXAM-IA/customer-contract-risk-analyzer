import streamlit as st
from azure.storage.blob import BlobServiceClient, ContentSettings
import tempfile
import mimetypes

AZURE_CONNECTION_STRING = ""
CONTAINER_NAME = "ccriskcontainer"

# Función para obtener MIME type
def get_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"

# Interfaz Streamlit
st.title("Subida de archivos a Azure Blob Storage")

uploaded_file = st.file_uploader("Selecciona un archivo", type=["pdf", "docx", "txt", "csv", "xlsx", "jpg", "png"])

def upload_file_to_azure(uploaded_files):
    for uploaded_file in uploaded_files: 
        if uploaded_file is not None:
            # Mostrar información básica del archivo
            st.write("Nombre del archivo:", uploaded_file.name)
            st.write("Tamaño:", uploaded_file.size, "bytes")

            try:
                # Crear cliente
                blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
                container_client = blob_service_client.get_container_client(CONTAINER_NAME)

                # Crear nombre del blob
                blob_name = f"test_data/{uploaded_file.name}"
                blob_client = container_client.get_blob_client(blob_name)

                # Leer el contenido y subir
                content_type = get_mime_type(uploaded_file.name)
                blob_client.upload_blob(
                    uploaded_file,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type)
                )

                # Confirmación y enlace
                blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
                st.success("Archivo subido correctamente")
                st.markdown(f"[Ver archivo en Azure Blob Storage]({blob_url})")

            except Exception as e:
                st.error(f"Error al subir el archivo: {e}")