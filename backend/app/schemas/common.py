from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = ""
