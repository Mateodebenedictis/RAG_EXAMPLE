from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import json

from entities import Project
from llm_components.loaders import S3FileLoader
from providers.opensearch import (
    content_vector_store,
    content_index_name,
    create_index_if_not_exists,
    delete_index_if_exists,
)
from providers.s3 import content_bucket_name, s3_client
from providers.analytics import Event, trackEvent
from providers.request import parse_api_gateway_request_body
from providers.sentry import sentry_sdk_init
from sentry_sdk import capture_exception

sentry_sdk_init()

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


def delete_content_index_and_return() -> dict:
    delete_index_if_exists(content_vector_store)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Content index deleted successfully!"}),
    }


def index_project(project: Project):
    trackEvent(
        Event(
            name="content_indexation",
            data={
                "customer_id": project.customer_id,
                "s3_keys": ",".join([asset.s3_key for asset in project.assets]),
            },
        )
    )

    all_documents = []

    for asset in project.assets:
        try:
            logger.info(f"Processing asset: {asset.asset_id}")
            loader = S3FileLoader(content_bucket_name, asset.s3_key, s3_client)
            documents = loader.load()
            documents[0].metadata["asset_id"] = asset.asset_id
            documents[0].metadata["customer_id"] = project.customer_id
            documents[0].metadata["project_id"] = asset.project_id
            documents[0].metadata["user_id"] = project.user_id or None

            all_documents.extend(documents)
        except Exception as e:
            logger.error(f"Error processing asset {asset.asset_id}: {str(e)}")
            raise

    logger.info(f"Total documents to index: {len(all_documents)}")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, add_start_index=True
    )

    split_docs = text_splitter.split_documents(all_documents)
    logger.info(f"Split documents into {len(split_docs)} chunks")
    ids = []

    for doc in split_docs:
        doc_id = f"{doc.metadata.get("asset_id")}-{doc.metadata.get("start_index")}"
        doc.metadata["id"] = doc_id
        ids.append(doc_id)

    try:
        create_index_if_not_exists(content_vector_store, content_index_name)
        content_vector_store.add_documents(
            documents=split_docs, ids=ids, bulk_size=len(split_docs)
        )
    except Exception as e:
        logger.error(f"Error adding documents to vector store: {str(e)}")
        raise

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Project indexing completed successfully",
                "indexed_ids": [asset.asset_id for asset in project.assets],
                "chunks": len(split_docs),
            }
        ),
    }


def lambda_handler(event, _):
    try:
        logger.info(
            f"Content parser lambda function invoked with event: {json.dumps(event, default=str)}"
        )
        if event["headers"].get("delete-index", "false") != "false":
            return delete_content_index_and_return()

        project = Project(**parse_api_gateway_request_body(event)["project"])
        result = index_project(project)
        logger.info(f"Project indexing completed. Result: {result}")
        return result
    except ValueError as e:
        logger.warning(f"Error while casting event: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": f"Error while casting event. Error occurred: {str(e)}"}
            ),
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        capture_exception(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Error occurred: {str(e)}"}),
        }
