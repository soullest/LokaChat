import glob
import boto3
import os

from typing import List
from langchain_aws import BedrockEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from opensearchpy import RequestsHttpConnection, OpenSearch
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.docstore.document import Document
from langchain.document_loaders import TextLoader
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

load_dotenv()

DOC_LOADERS_MAPPING = {
    ".md": (TextLoader, {"encoding": "utf8"}),
}


def load_document(path: str) -> Document:
  try:
    ext = "." + path.rsplit(".", 1)[-1]
    if ext in DOC_LOADERS_MAPPING:
      loader_class, loader_args = DOC_LOADERS_MAPPING[ext]
      loader = loader_class(path, **loader_args)

      return loader.load()[0]

    raise ValueError(f"Unsupported file extension: {ext}")
  except Exception as exception:
    raise ValueError(f"Error loading document: {exception}")


def load_documents_from_dir(path: str) -> List[Document]:
  try:
    all_files = []
    for ext in DOC_LOADERS_MAPPING:
      all_files.extend(
        glob.glob(os.path.join(path, f"**/*{ext}"), recursive=True)
      )

    return [load_document(path) for path in all_files]
  except Exception as exception:
    raise RuntimeError(f"Error loading files: {exception}")


def store_data() -> None:

  boto_session = boto3.session.Session(
          aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
          aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
      )
  bedrock_runtime = boto_session.client(
          service_name="bedrock-runtime",
          region_name="us-east-1",
      )

  #embedding = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1")
  credentials = boto_session.get_credentials()

  bedrock_embeddings = BedrockEmbeddings(client=bedrock_runtime, model_id="amazon.titan-embed-text-v1")

  awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, "us-east-1", "aoss", session_token=credentials.token)
  #awsauth = AWS4Auth(os.environ["AWS_ACCESS_KEY"], os.environ["AWS_SECRET_ACCESS_KEY"], "us-east-1", "aoss")
  opensearch_domain_endpoint = os.environ['OPEN_SEARCH_ENDPOINT']
  opensearch_index = os.environ['OPEN_SEARCH_INDEX']

  vector = OpenSearchVectorSearch(
    embedding_function=bedrock_embeddings,
    index_name=opensearch_index,
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    http_compress=True,
    connection_class=RequestsHttpConnection,
    opensearch_url=opensearch_domain_endpoint
  )

  # Cargar todos los archivos .md desde la carpeta 'data'
  data = load_documents_from_dir("./data/")

  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
  splits = text_splitter.split_documents(data)
  vector.add_documents(
    documents=splits,
    vector_field="rag_vector",
    bulk_size=3000
  )


def query():
  boto_session = boto3.session.Session(
    aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
  )
  bedrock_runtime = boto_session.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
  )

  # embedding = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1")
  credentials = boto_session.get_credentials()

  bedrock_embeddings = BedrockEmbeddings(client=bedrock_runtime, model_id="amazon.titan-embed-text-v1")

  awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, "us-east-1", "aoss",
                     session_token=credentials.token)
  # awsauth = AWS4Auth(os.environ["AWS_ACCESS_KEY"], os.environ["AWS_SECRET_ACCESS_KEY"], "us-east-1", "aoss")
  opensearch_domain_endpoint = os.environ['OPEN_SEARCH_ENDPOINT']
  opensearch_index = os.environ['OPEN_SEARCH_INDEX']

  vector = OpenSearchVectorSearch(
    embedding_function=bedrock_embeddings,
    index_name=opensearch_index,
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    http_compress=True,
    connection_class=RequestsHttpConnection,
    opensearch_url=opensearch_domain_endpoint
  )
  question = "regions available?"
  results = vector.similarity_search(
    question,
    vector_field="rag_vector",
    text_field="text",
    metadata_field="metadata",
    k=10
  )

  rr = [{"page_content": r.page_content, "metadata": r.metadata} for r in results]
  data = ""
  for doc in rr:
    print(doc['metadata'])
    data += doc['page_content'] + "\n\n"

  print('#'*20)
  print(data)
  print('#' * 20)


if __name__ == "__main__":
    query()

