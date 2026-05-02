from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class BasicJobRequest(BaseModel):
    feed_url: str
    links_to_footnotes: bool = False
    add_toc: bool = True
    include_images: bool = True
    max_posts: int = Field(default=250, ge=1)
    post_range_start: int = Field(default=1, ge=1)
    post_range_end: int | None = Field(default=None, ge=1)


class CustomSelector(BaseModel):
    tag_name: str = ""
    attr_name: str = ""
    attr_value: str = ""
    pre_string: str = ""
    parent_tag: bool = False


class AdvancedJobRequest(BaseModel):
    starting_url: str
    starting_title: str
    site_url: str
    site_title: str
    site_description: str = ""
    links_to_footnotes: bool = False
    add_toc: bool = True
    include_images: bool = True
    max_posts: int = Field(default=250, ge=1)
    post_range_start: int = Field(default=1, ge=1)
    post_range_end: int | None = Field(default=None, ge=1)
    custom_selector: Optional[CustomSelector] = None
