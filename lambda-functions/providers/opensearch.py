import logging
import os

from langchain_community.vectorstores import OpenSearchVectorSearch
from opensearchpy import RequestsHttpConnection, OpenSearch

from .bedrock import content_embeddings, layout_embeddings, find_index_dimension


_logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)

region = os.getenv("OPENSEARCH_AWS_REGION", "us-west-1")
host = os.getenv("OPENSEARCH_ENDPOINT", "")
content_index_name = os.getenv("OPENSEARCH_CONTENT_INDEX", "content_vector_embeddings")
layout_index_name = os.getenv("OPENSEARCH_LAYOUT_INDEX", "layout_vector_embeddings")
opensearch_username = os.getenv("OPENSEARCH_USERNAME", "admin")
opensearch_password = os.getenv("OPENSEARCH_PASSWORD", "temporaryP4ssw*rd")

auth = (opensearch_username, opensearch_password)

search_client = OpenSearch(
    hosts=host,
    http_auth=auth,
    http_compress=True,
    use_ssl=True,
    verify_certs=True,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
    timeout=30,
    max_retries=3,
    connection_class=RequestsHttpConnection,
    pool_maxsize=20,
)

content_vector_store = OpenSearchVectorSearch(
    index_name=content_index_name,
    embedding_function=content_embeddings,
    opensearch_url=host,
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

layout_vector_store = OpenSearchVectorSearch(
    index_name=layout_index_name,
    embedding_function=layout_embeddings,
    opensearch_url=host,
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)


def create_index_if_not_exists(store: OpenSearchVectorSearch, index_name: str) -> None:
    if not store.index_exists():
        _logger.info(f"{index_name} Index does not exist. Creating...")
        store.create_index(
            find_index_dimension(store.embeddings),
            index_name,
            is_appx_search=False,
            http_auth=auth,
        )
        _logger.info(f"{index_name} Index created successfully!")


def delete_index_if_exists(store: OpenSearchVectorSearch) -> None:
    if store.index_exists():
        _logger.info(f"Deleting {store.index_name} index...")
        store.delete_index()
        _logger.info(f"{store.index_name} index deleted successfully!")
