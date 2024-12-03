from pydantic import BaseModel


class ToDo(BaseModel):
    timestamp: int
    titel: str
    msg: str
    level: int


class Information(BaseModel):
    timestamp: int
    summary: str
    detail: str
    level: int


class DeleteBody(BaseModel):
    timestamp: int
