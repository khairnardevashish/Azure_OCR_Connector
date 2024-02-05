import streamlit as st
from azure.storage.blob import BlobServiceClient
import requests
import time
import json
import os

# Function to upload file to Azure Blob Storage
def upload_to_azure_blob(file_path, connection_string, container_name):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=os.path.basename(file_path))

    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    return blob_client.url

# Function to extract invoice information
def extract_invoice_information(content):
    content_dict = json.loads(content)
    invoice_date = content_dict.get("Invoice Date", {}).get("text", "N/A")
    due_date = content_dict.get("Due Date", {}).get("text", "N/A")
    total_due = content_dict.get("Total Due", {}).get("text", "N/A")
    return invoice_date, due_date, total_due

# Function to analyze document using Azure Form Recognizer
def analyze_document(endpoint, model_id, api_version, subscription_key, document_url):
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": subscription_key,
    }

    data = {
        "urlSource": document_url
    }

    url = f"{endpoint}/formrecognizer/documentModels/{model_id}:analyze?api-version={api_version}"

    response = requests.post(url, headers=headers, json=data)
    result_id = response.headers["Operation-Location"].split("/")[-1].split("?")[0]
    return result_id

# Function to get results using Azure Form Recognizer GET request
def get_document_results(endpoint, model_id, result_id, api_version, subscription_key):
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
    }

    url = f"{endpoint}/formrecognizer/documentModels/{model_id}/analyzeResults/{result_id}?api-version={api_version}"
    time.sleep(2)
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()

# Function to display tables
def display_tables(json_data):
    try:
        for i, data in enumerate(json_data['analyzeResult']['tables']):
            st.subheader(f'Table {i+1}')
            table = {}
            for cell in data["cells"]:
                row_index = cell["rowIndex"]
                col_index = cell["columnIndex"]
                content = cell["content"]
                if row_index not in table:
                    table[row_index] = {}
                table[row_index][col_index] = content

            # Display table using Streamlit
            st.table(table)

    except KeyError:
        st.warning("No table present in the file")

# Main Flow
st.set_page_config(page_title="Invoice Analyzer", page_icon=":chart_with_upwards_trend:")

st.title("Azure OCR Connector for Invoice")

# File Upload Section
uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"])

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    # Display file details
    st.write("### File Details:")
    st.write(f"**Name:** {uploaded_file.name} | **Type:** {uploaded_file.type} | **Size:** {uploaded_file.size / 1024:.2f} KB")

    # Upload to Azure Blob Storage button
    if st.button("Upload to Azure Blob Storage"):
        st.info("Uploading file to Storage...")

        # Save the uploaded file temporarily
        temp_file_path = f"temp_{uploaded_file.name}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(uploaded_file.getvalue())

        # Specify your Azure Storage account connection string and container name
        connection_string = 'DefaultEndpointsProtocol=https;AccountName=ezstorage97;AccountKey=24HqJJ/XTu+Dv7XFpsqGVRmHquJbhwKX9lyl66LalObvjFceaICdzUwqUSpv8D8UhepjumOaCD40+AStn/WSdA==;EndpointSuffix=core.windows.net'
        container_name = 'ezofic2'

        # Upload file to Azure Blob Storage and get the public URL
        blob_url = upload_to_azure_blob(temp_file_path, connection_string, container_name)

        # Display the public URL
        st.success(f"File uploaded successfully! [**View File**]({blob_url})")

        # Remove the temporary file
        os.remove(temp_file_path)

        # Specify your Azure Form Recognizer API details
        form_recognizer_endpoint = 'https://ezofic.cognitiveservices.azure.com/'
        form_recognizer_model_id = 'prebuilt-invoice'
        form_recognizer_api_version = '2023-07-31'
        form_recognizer_subscription_key = 'd9bb3050f0f447de98cb00ddaa9e3c4b'

        # Analyze document using Azure Form Recognizer POST request
        result_id = analyze_document(form_recognizer_endpoint, form_recognizer_model_id, form_recognizer_api_version,
                                     form_recognizer_subscription_key, blob_url)

        st.info(f"Document analysis initiated. Result ID: {result_id}")

        # Get results using Azure Form Recognizer GET request
        results = get_document_results(form_recognizer_endpoint, form_recognizer_model_id, result_id,
                                       form_recognizer_api_version, form_recognizer_subscription_key)

        st.success("Document analysis completed!")

        # Remove "pages" key
        if "pages" in results["analyzeResult"]:
            del results["analyzeResult"]["pages"]

        # Display extracted invoice information
        # invoice_date, due_date, total_due = extract_invoice_information(results["analyzeResult"])
        # st.write("### Extracted Invoice Information:")
        # st.write(f"**Invoice Date:** {invoice_date}")
        # st.write(f"**Due Date:** {due_date}")
        # st.write(f"**Total Due:** {total_due}")

        # Display tables if present
        display_tables(results)

        st.write(f"Results saved to [local_results.json](local_results.json)")
