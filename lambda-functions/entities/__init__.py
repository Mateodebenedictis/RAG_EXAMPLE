from typing import List, Optional, Any
from pydantic import BaseModel, field_validator
import json


class Asset(BaseModel):
    asset_id: str
    project_id: str
    s3_key: str


class Project(BaseModel):
    customer_id: str
    user_id: Optional[str] = None
    assets: List[Asset]


class Template(BaseModel):
    customer_id: str
    s3_keys: List[str]


class GenerationInput(BaseModel):
    prompt: str
    customer_id: str
    slide_amount: int
    content_project_id: Optional[str] = None
    content_asset_ids: Optional[List[str]] = None
    template_project_name: Optional[str] = None
    template_slide_filenames: Optional[List[str]] = None

    @field_validator("slide_amount")
    @classmethod
    def slide_amount_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("slide_amount must be positive")
        return v

    @field_validator("slide_amount", mode="before")
    @classmethod
    def parse_slide_amount(cls, v: Any) -> int:
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                raise ValueError("slide_amount must be a valid integer")
        elif not isinstance(v, int):
            raise ValueError("slide_amount must be an integer")
        return v


class GenerationOutput(BaseModel):
    json_slides: List[str]

    def to_dict(self):
        result = {}
        for index, slide in enumerate(self.json_slides, start=1):
            try:
                slide_content = json.loads(slide)
            except json.JSONDecodeError:
                slide_content = slide

            result[f"slide-{index}"] = slide_content

        return result
