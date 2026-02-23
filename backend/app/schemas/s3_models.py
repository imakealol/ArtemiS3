from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class S3ObjectModel(BaseModel):
    key: str
    size: int
    last_modified: Optional[datetime] = None
    storage_class: Optional[str] = None


class S3FolderModel(BaseModel):
    path: str
    name: str
    depth: int
    matched_count: int


class S3BreadcrumbModel(BaseModel):
    path: str
    name: str


class S3FolderChildrenResponse(BaseModel):
    path: str
    breadcrumbs: List[S3BreadcrumbModel]
    children: List[S3FolderModel]
    files: List[S3ObjectModel]
