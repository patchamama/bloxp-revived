from typing import Optional
from pydantic import BaseModel, HttpUrl


class BasicJobRequest(BaseModel):
    feed_url: str
    links_to_footnotes: bool = False
    add_toc: bool = True
    include_images: bool = True


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
    max_posts: int = 250
    custom_selector: Optional[CustomSelector] = None
