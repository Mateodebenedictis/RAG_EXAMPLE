import os

from boto3 import client
from langchain_aws import BedrockEmbeddings, ChatBedrock
from langchain_core.embeddings import Embeddings

bedrock_region = os.getenv("BEDROCK_AWS_REGION", "us-west-2")
content_model_id = os.getenv("BEDROCK_CONTENT_EMBEDDING_MODEL_ID", "")
layout_model_id = os.getenv("BEDROCK_LAYOUT_EMBEDDING_MODEL_ID", "")
generation_model_id = os.getenv("BEDROCK_GENERATION_MODEL_ID", "")

bedrock_client = client(
    service_name="bedrock-runtime",
    region_name=bedrock_region,
)

content_embeddings = BedrockEmbeddings(
    model_id=content_model_id, region_name=bedrock_region, client=bedrock_client
)

layout_embeddings = BedrockEmbeddings(
    model_id=layout_model_id, region_name=bedrock_region, client=bedrock_client
)

llm = ChatBedrock(
    model_id=generation_model_id,
    region_name=bedrock_region,
    client=bedrock_client,
    model_kwargs={
        "max_tokens": 8192,
        "temperature": 0.7,
        "top_p": 0.9,
    },
)


def find_index_dimension(embedding_model: Embeddings) -> int:
    embedding = embedding_model.embed_documents(["test"])
    return len(embedding[0])
