import glob
import boto3
import os

from typing import List
from collections import Counter
from langchain_aws import BedrockEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from opensearchpy import RequestsHttpConnection, OpenSearch
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.docstore.document import Document
from langchain.document_loaders import TextLoader
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

load_dotenv()


class AOSSEmbeddings:

    def __init__(self, model_id: str = "amazon.titan-embed-text-v1"):
        self.DOC_LOADERS_MAPPING = {
          ".md": (TextLoader, {"encoding": "utf8"}),
        }

        self.boto_session = boto3.session.Session(
          aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
          aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"]
        )
        self.bedrock_runtime = self.boto_session.client(
          service_name="bedrock-runtime",
          region_name="us-east-1",
        )

        self.credentials = self.boto_session.get_credentials()
        self.model_id = model_id
        self.bedrock_embeddings = BedrockEmbeddings(client=self.bedrock_runtime, model_id=self.model_id)

        self.awsauth = AWS4Auth(self.credentials.access_key, self.credentials.secret_key, "us-east-1", "aoss",
                                session_token=self.credentials.token)

        self.opensearch_domain_endpoint = os.environ['OPEN_SEARCH_ENDPOINT']
        self.opensearch_index = os.environ['OPEN_SEARCH_INDEX']

        self.vector = OpenSearchVectorSearch(
          embedding_function=self.bedrock_embeddings,
          index_name=self.opensearch_index,
          http_auth=self.awsauth,
          use_ssl=True,
          verify_certs=True,
          http_compress=True,
          connection_class=RequestsHttpConnection,
          opensearch_url=self.opensearch_domain_endpoint
        )

    def load_document(self, path: str) -> Document:
        try:
            ext = "." + path.rsplit(".", 1)[-1]
            if ext in self.DOC_LOADERS_MAPPING:
                loader_class, loader_args = self.DOC_LOADERS_MAPPING[ext]
                loader = loader_class(path, **loader_args)

                return loader.load()[0]

            raise ValueError(f"Unsupported file extension: {ext}")
        except Exception as exception:
            raise ValueError(f"Error loading document: {exception}")

    def load_documents_from_dir(self, path: str) -> List[Document]:
        try:
            all_files = []
            for ext in self.DOC_LOADERS_MAPPING:
                all_files.extend(
                    glob.glob(os.path.join(path, f"**/*{ext}"), recursive=True)
                )

            return [self.load_document(path) for path in all_files]
        except Exception as exception:
            raise RuntimeError(f"Error loading files: {exception}")

    def store_data(self) -> None:
        # Cargar todos los archivos .md desde la carpeta 'data'
        data = self.load_documents_from_dir("./data/")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
        splits = text_splitter.split_documents(data)
        self.vector.add_documents(
            documents=splits,
            vector_field="rag_vector",
            bulk_size=3000
        )

    def query(self, question: str = '', k: int = 5, links_dict={}):
        results = self.vector.similarity_search(
            question,
            vector_field="rag_vector",
            text_field="text",
            metadata_field="metadata",
            k=k,
        )

        rr = [{"page_content": r.page_content, "metadata": r.metadata} for r in results]
        data = ""
        meta_files = []
        for doc in rr:
            data += f"""
            {doc['page_content']}
            """
            meta_files.append(doc['metadata']['source'])
            print(doc['metadata'])

        conteo = Counter(meta_files)
        files_sorted = [elem for elem, _ in conteo.most_common()]
        files_html = ""
        for f in files_sorted:
            file_name = str(f).replace('./data\\', '')
            files_html = f"""{files_html}<p><a href="{links_dict[file_name]}">{file_name}</a></p>"""
        # files_str = "\n\n\t\t•".join(map(str, files_sorted))

        print('#' * 20)
        print(data)
        print(meta_files)
        print('#' * 20)

        return data, files_html
