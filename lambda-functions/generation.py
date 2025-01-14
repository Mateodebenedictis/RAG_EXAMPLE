from datetime import datetime
import logging
import json
import re
from sentry_sdk import capture_exception
from typing import List, Dict, Any, Optional

from langchain_community.vectorstores.opensearch_vector_search import (
    SCRIPT_SCORING_SEARCH,
)
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.vectorstores.base import VectorStoreRetriever

from entities import GenerationInput, GenerationOutput
from providers.opensearch import (
    content_vector_store,
    layout_vector_store,
    content_index_name,
)
from providers.bedrock import llm
from providers.analytics import Event, trackEvent
from providers.request import parse_api_gateway_request_body
from providers.s3 import generation_output_bucket_name, s3_client
from providers.sentry import sentry_sdk_init
from llm_components.prompts import layout_llm_prompt, content_generation_final_prompt
from llm_components.formatters import (
    extract_metadata,
    format_presentation_content,
    format_layout_documents,
)

sentry_sdk_init()

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


def content_query_search(
    prompt: str,
    customer_id: str,
    project_id: Optional[str] = None,
    asset_ids: Optional[List[str]] = None,
) -> List[Document]:
    """Query OpenSearch with embedding and filters using OpenSearchVectorSearch."""

    logger.info(
        f"Starting content query search for customer_id: {customer_id}, project_id: {project_id}, asset_ids: {asset_ids}"
    )
    query_filter: List[Dict[str, Any]] = [
        {"term": {"metadata.customer_id.keyword": customer_id}}
    ]
    if asset_ids:
        query_filter.append({"terms": {"metadata.asset_id.keyword": asset_ids}})
    elif project_id:
        query_filter.append({"term": {"metadata.project_id.keyword": project_id}})

    try:
        logger.info(f"Executing OpenSearch with index: {content_index_name}")
        results = content_vector_store.similarity_search(
            query=prompt,
            k=20,
            search_type=SCRIPT_SCORING_SEARCH,
            pre_filter={"bool": {"filter": query_filter}},
        )
        logger.debug(f"OpenSearch results: {results}")
        logger.info(f"OpenSearch query returned {len(results)} results")
        return results
    except Exception as e:
        logging.error(f"Error during OpenSearch query: {str(e)}")
        raise


def invoke_llm(prompt: str):
    """Invoke llm and log the token consumption"""

    response = llm.invoke(prompt)

    logging.info(
        f"Generation metadata: {json.dumps(extract_metadata(response), indent=2)}"
    )

    return response


def content_generation_process(
    prompt: str,
    customer_id: str,
    project_id: Optional[str] = None,
    asset_ids: Optional[List[str]] = None,
    slides: int = 5,
):
    """Full content generation process"""

    trackEvent(
        Event(
            name="content_generation_process",
            data={
                "customer_id": customer_id,
                "project_id": project_id if project_id else "",
                "asset_ids": ",".join(asset_ids) if asset_ids else "",
                "prompt": prompt,
                "slides": str(slides),
            },
        )
    )

    logger.info(
        f"Starting content generation process for customer_id: {customer_id}, project_id: {project_id}, asset_ids: {asset_ids}"
    )

    try:
        logger.info("Querying for filtered embeddings")
        filtered_embeddings = content_query_search(
            prompt, customer_id, project_id, asset_ids
        )

        if not filtered_embeddings:
            logger.warning("No filtered embeddings found")
            context = ""
        else:
            context = "\n".join(
                [document.page_content for document in filtered_embeddings]
            )

        content_prompt = content_generation_final_prompt(context, prompt, slides)
        llm_response = invoke_llm(content_prompt)

        return format_presentation_content(llm_response.content)
    except Exception as e:
        logging.error(f"Error in RAG process: {str(e)}")
        raise


def layout_generation_process(
    slide_content: str,
    customer_id: str,
    template_project_name: Optional[str] = None,
    template_slide_filenames: Optional[List[str]] = None,
) -> List[str]:
    """Full layout generation process"""

    trackEvent(
        Event(
            name="layout_generation_process",
            data={
                "customer_id": customer_id,
                "template_project_name": (
                    template_project_name if template_project_name else ""
                ),
                "template_slide_filenames": (
                    ",".join(template_slide_filenames)
                    if template_slide_filenames
                    else ""
                ),
            },
        )
    )

    logger.info(
        f"Starting layout generation process for customer_id: {customer_id}, template_project_name: {template_project_name}, template_slide_filenames: {template_slide_filenames}"
    )

    retriever = retrieve_vector_embeddings(
        customer_id, template_project_name, template_slide_filenames
    )
    llm_prompt = PromptTemplate.from_template(layout_llm_prompt)
    chain = (
        {"layouts": retriever | format_layout_documents, "slide": RunnablePassthrough()}
        | llm_prompt
        | invoke_llm
        | StrOutputParser()
    )
    # The regex pattern corresponds to the layout of the content
    slides = re.findall(
        r"\[Slide \d+\](.*?)(?=\[Slide \d+\]|$)", slide_content, re.DOTALL
    )

    json_slides = []
    for i, slide in enumerate(slides):
        logger.info(f"Processing slide {i+1}/{len(slides)}")
        logger.debug(
            f"Candidate slides for slide {i+1}: {[doc.metadata['id'] for doc in retriever.invoke(slide)]}"
        )

        json_slide = chain.invoke(slide)
        json_slides.append(json_slide)
        logger.info(f"Generated layout for slide {i+1}")

    logger.info(
        f"Layout generation complete. Generated {len(json_slides)} slide layouts"
    )
    return json_slides


def retrieve_vector_embeddings(
    customer_id: str,
    template_project_name: Optional[str] = None,
    template_slide_filenames: Optional[List[str]] = None,
) -> VectorStoreRetriever:
    """Retrieves vector embeddings from a vector store for a given project."""

    query_filter: List[Dict[str, Any]] = []

    if template_slide_filenames:
        query_filter.append(
            {"terms": {"metadata.slide_filename.keyword": template_slide_filenames}}
        )
    elif template_project_name:
        query_filter.append(
            {"term": {"metadata.template_project_name.keyword": template_project_name}}
        )
    else:
        query_filter.append({"term": {"metadata.customer_id.keyword": customer_id}})

    logger.info(f"Querying vector store with filter: {query_filter}")

    return layout_vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 3,
            "search_type": SCRIPT_SCORING_SEARCH,
            "pre_filter": {"bool": {"filter": query_filter}},
        },
    )


def run_generation(generation: GenerationInput) -> GenerationOutput:
    """Run the content and template generation"""
    content = content_generation_process(
        generation.prompt,
        generation.customer_id,
        generation.content_project_id,
        generation.content_asset_ids,
        generation.slide_amount,
    )
    json_slides = layout_generation_process(
        content,
        generation.customer_id,
        generation.template_project_name,
        generation.template_slide_filenames,
    )
    save_output_to_s3(json_slides)
    return GenerationOutput(json_slides=json_slides)


def save_output_to_s3(json_slides: List[str]):
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    errors = []

    for i, slide_content in enumerate(json_slides):
        key = f"{timestamp}/slide-{i+1}.json"

        try:
            s3_client.put_object(
                Bucket=generation_output_bucket_name,
                Key=key,
                Body=slide_content,
                ContentType="application/json",
            )
            logger.info(f"Successfully saved slide {i+1} to S3: {key}")
        except Exception as e:
            error_message = f"Error saving slide {i+1} to S3: {str(e)}"
            logger.error(error_message)
            errors.append(error_message)

    if errors:
        raise Exception(
            f"Errors occurred while saving slides to S3: {'\n'.join(errors)}"
        )
    else:
        logger.info(f"Successfully saved all {len(json_slides)} slides to S3")


def lambda_handler(event, _):
    try:
        logger.info(
            f"Generation lambda function invoked with event: {json.dumps(event, default=str)}"
        )
        generation = GenerationInput(
            **parse_api_gateway_request_body(event)["generation"]
        )
        generation_output = run_generation(generation)
        logger.debug(f"Generation output: {json.dumps(generation_output.to_dict())}")
        return {
            "statusCode": 200,
            "body": json.dumps(generation_output.to_dict()),
        }
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
