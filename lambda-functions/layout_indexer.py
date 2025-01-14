import json
import logging

from entities import Template
from llm_components.loaders import S3FileLoader
from providers.opensearch import (
    create_index_if_not_exists,
    delete_index_if_exists,
    layout_index_name,
    layout_vector_store,
)
from providers.s3 import layout_bucket_name, s3_client
from providers.analytics import Event, trackEvent
from providers.request import parse_api_gateway_request_body
from providers.sentry import sentry_sdk_init
from sentry_sdk import capture_exception

sentry_sdk_init()

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


def delete_layout_index_and_return() -> dict:
    delete_index_if_exists(layout_vector_store)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Layout index deleted successfully!"}),
    }


def index_template(template: Template):

    trackEvent(
        Event(
            name="layout_indexation",
            data={
                "customer_id": template.customer_id,
                "s3_keys": ",".join(template.s3_keys),
            },
        )
    )

    try:
        logger.info(f"Starting indexing for template: {template}")
        data = load_jsons(template)

        if data:
            logger.info(f"Loaded {len(data)} JSON files")
            create_index_if_not_exists(layout_vector_store, layout_index_name)
            index_json_files(data)
            indexed_ids = get_json_ids_from_array(data)
            logger.info(f"Indexing completed. Indexed IDs: {indexed_ids}")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Indexing completed successfully",
                        "indexed_ids": indexed_ids,
                    }
                ),
            }
        else:
            logger.info("No files to index")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No files to index", "indexed_ids": []}),
            }
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        capture_exception(e)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": f"Error occurred: {str(e)}", "indexed_ids": []}
            ),
        }


def load_jsons(template: Template):
    data = []

    for s3_key in template.s3_keys:
        try:
            logger.info(f"Loading file from S3. S3 Key: {s3_key}")
            loader = S3FileLoader(layout_bucket_name, s3_key, s3_client)
            documents = loader.load()
            documents[0].metadata.update(
                process_layout_metadata(
                    json.loads(documents[0].page_content), template.customer_id
                )
            )
            data.extend(documents)
            logger.info(f"Successfully loaded and processed file. S3 Key: {s3_key}")
        except s3_client.exceptions.NoSuchKey:
            logger.warning(f"File not found for document with S3 Key: {s3_key}")

    return data


def process_layout_metadata(record: dict, customer_id: str) -> dict:
    logger.info("Processing layout metadata")
    metadata = {}
    template_name = record.get("project", {}).get("name", "")
    template_name_slug: str = template_name.replace(" ", "-").lower()
    slide_name_slug = record.get("project", {}).get("title", "")

    metadata["customer_id"] = customer_id
    metadata["slide_filename"] = slide_name_slug
    metadata["template_project_name"] = template_name
    metadata["id"] = f"{customer_id}-{template_name_slug}-{slide_name_slug}"

    logger.info(f"Processed metadata: {metadata}")
    return metadata


def index_json_files(data):
    logger.info(f"Indexing {len(data)} JSON files")
    layout_vector_store.add_documents(
        documents=data,
        ids=[doc.metadata.get("id") for doc in data],
    )


def get_json_ids_from_array(json_list):
    ids = [doc.metadata.get("id") for doc in json_list if doc.metadata.get("id")]
    return ids


def lambda_handler(event, _):
    try:
        logger.info(
            f"Layout parser lambda function invoked with event: {json.dumps(event, default=str)}"
        )
        if event["headers"].get("delete-index", "false") != "false":
            return delete_layout_index_and_return()

        template = Template(**parse_api_gateway_request_body(event)["template"])
        return index_template(template)
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
            "body": json.dumps(
                {"message": f"Error occurred: {str(e)}", "indexed_ids": []}
            ),
        }
