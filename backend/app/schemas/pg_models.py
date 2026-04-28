from pydantic import BaseModel


class TagRecord(BaseModel):
    hashed_key: str
    bucket: str
    tags: list[str]

class MimeRecord(BaseModel):
    extension: str
    mime_type: str