# schemas/todo.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class TodoResponse(TodoBase):
    id: str
    created_at: datetime
    updated_at: datetime
    deleted: bool = False
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    current_page: int
    total_pages: int
    items_per_page: int
    total_items: int
    data: List[TodoResponse]
