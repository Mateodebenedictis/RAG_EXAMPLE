from langchain_core.documents import Document
from langchain_community.document_loaders.base import BaseLoader
from typing import Any, Callable, Iterator, List, Optional, TYPE_CHECKING
from typing_extensions import TypeAlias


if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
else:
    S3Client = Any

Element: TypeAlias = Any


class S3FileLoader(BaseLoader):
    """
    Load from `Amazon AWS S3` file.

    COPIED FROM langchain_community.document_loaders.s3_file.S3FileLoader
    AND langchain_community.document_loaders.unstructured.UnstructuredBaseLoader
    (langchain_community version 0.2.12)

    **But there are 2 key changes:**
    1. We are removing the hidden dependency with Unstructured, instead just using a simple loader.
    2. We're passing the full boto3 S3 client instead of configuration parameters.
    """

    def __init__(
        self,
        bucket: str,
        key: str,
        s3_client: S3Client,
        *,
        post_processors: Optional[List[Callable]] = None,
    ):
        """Initialize with bucket and key name.

        :param bucket: The name of the S3 bucket.
        :param key: The key of the S3 object.
        :param s3_client: The boto3 S3 client.
        :param post_processors: Post processing functions to be applied to
            extracted elements.
        """
        super().__init__()
        self.bucket = bucket
        self.key = key
        self.s3_client = s3_client
        self.post_processors = post_processors or []

    def _get_elements(self) -> List:
        """Get elements."""
        result = self.s3_client.get_object(Bucket=self.bucket, Key=self.key)

        return [result.get("Body").read().decode("utf-8")]

    def _get_metadata(self) -> dict:
        return {"source": f"s3://{self.bucket}/{self.key}"}

    def _post_process_elements(self, elements: List[Element]) -> List[Element]:
        """Apply post processing functions to extracted unstructured elements.

        Post processing functions are str -> str callables passed
        in using the post_processors kwarg when the loader is instantiated.
        """
        for element in elements:
            for post_processor in self.post_processors:
                element.apply(post_processor)
        return elements

    def lazy_load(self) -> Iterator[Document]:
        """Load file."""
        elements = self._get_elements()
        metadata = self._get_metadata()
        self._post_process_elements(elements)
        text = "\n\n".join([str(el) for el in elements])
        yield Document(page_content=text, metadata=metadata)
