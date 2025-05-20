# routes/todo.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from pymongo.collection import Collection
from bson import ObjectId

from app.database import get_db_collection
from app.models import create_todo_document, format_todo_response
from schemas.todo import TodoCreate, TodoUpdate, TodoResponse, PaginatedResponse

router = APIRouter(
    prefix="/todos",
    tags=["todos"]
)

@router.post("/", response_model=TodoResponse)
def create_todo(todo: TodoCreate, collection: Collection = Depends(get_db_collection)):
    """
    Create a new todo item
    """
    try:
        # Create a new todo document
        todo_dict = todo.model_dump()
        todo_document = create_todo_document(todo_dict)
        
        # Insert into MongoDB
        result = collection.insert_one(todo_document)
        
        # Get the created document
        created_todo = collection.find_one({"_id": result.inserted_id})
        return format_todo_response(created_todo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/", response_model=PaginatedResponse)
def read_todos(
    include_deleted: bool = False,
    sort_by: Optional[str] = Query(None, enum=["date", "completed"]),
    items_per_page: int = Query(20, gt=0),
    page_number: int = Query(1, gt=0),
    collection: Collection = Depends(get_db_collection)
):
    """
    Retrieve a list of todo items with pagination and sorting
    """
    # Build query filter
    query_filter = {} if include_deleted else {"deleted": False}
    
    # Count total items
    total_items = collection.count_documents(query_filter)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Calculate skip
    skip = (page_number - 1) * items_per_page
    
    # Apply sorting
    sort_options = []
    if sort_by == "date":
        sort_options.append(("created_at", -1))  # -1 for descending order
    elif sort_by == "completed":
        sort_options.append(("completed", -1))  # -1 for descending order
    
    # Return empty data if skip exceeds total items
    if skip >= total_items:
        return PaginatedResponse(
            current_page=page_number,
            total_pages=total_pages,
            items_per_page=items_per_page,
            total_items=total_items,
            data=[]
        )
    
    # Fetch the paginated data
    cursor = collection.find(query_filter)
    
    # Apply sorting if specified
    if sort_options:
        cursor = cursor.sort(sort_options)
    
    # Apply pagination
    cursor = cursor.skip(skip).limit(items_per_page)
    
    # Convert MongoDB documents to TodoResponse objects
    todos = [format_todo_response(todo) for todo in cursor]
    
    # Build the response
    response = PaginatedResponse(
        current_page=page_number,
        total_pages=total_pages,
        items_per_page=items_per_page,
        total_items=total_items,
        data=todos
    )
    
    return response

@router.get("/{todo_id}", response_model=TodoResponse)
def read_todo(todo_id: str, collection: Collection = Depends(get_db_collection)):
    """
    Retrieve a specific todo item by ID
    """
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(todo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    todo = collection.find_one({"_id": obj_id})
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    # Check if todo is soft deleted
    if todo.get("deleted", False):
        raise HTTPException(status_code=404, detail="Todo was deleted")
    
    return format_todo_response(todo)

@router.put("/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: str, todo: TodoUpdate, collection: Collection = Depends(get_db_collection)):
    """
    Update a specific todo item
    """
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(todo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Find the todo
    db_todo = collection.find_one({"_id": obj_id})
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    # Check if todo is soft deleted
    if db_todo.get("deleted", False):
        raise HTTPException(status_code=400, detail="Cannot update deleted todo")
    
    # Prepare update data
    update_data = {k: v for k, v in todo.model_dump(exclude_unset=True).items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.now()
        
        # Update in MongoDB
        collection.update_one({"_id": obj_id}, {"$set": update_data})
    
    # Get updated todo
    updated_todo = collection.find_one({"_id": obj_id})
    return format_todo_response(updated_todo)

@router.delete("/{todo_id}", response_model=TodoResponse)
def delete_todo(todo_id: str, permanent: bool = False, collection: Collection = Depends(get_db_collection)):
    """
    Soft delete or permanently delete a specific todo item
    """
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(todo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Find the todo
    db_todo = collection.find_one({"_id": obj_id})
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    try:
        if permanent:
            # Permanent delete
            collection.delete_one({"_id": obj_id})
        else:
            # Soft delete
            collection.update_one(
                {"_id": obj_id},
                {"$set": {"deleted": True, "deleted_at": datetime.now()}}
            )
        
        return format_todo_response(db_todo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{todo_id}/restore", response_model=TodoResponse)
def restore_todo(todo_id: str, collection: Collection = Depends(get_db_collection)):
    """
    Restore a soft-deleted todo item
    """
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(todo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Find the todo
    db_todo = collection.find_one({"_id": obj_id})
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    if not db_todo.get("deleted", False):
        raise HTTPException(status_code=400, detail="Todo is not deleted")
    
    try:
        # Restore the todo
        collection.update_one(
            {"_id": obj_id},
            {"$set": {"deleted": False, "deleted_at": None}}
        )
        
        # Get updated todo
        restored_todo = collection.find_one({"_id": obj_id})
        return format_todo_response(restored_todo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")



# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from typing import List
# from sqlalchemy.exc import SQLAlchemyError

# from app.database import get_db
# from app.models import Todo
# from schemas.todo import TodoCreate, TodoUpdate, TodoResponse

# router = APIRouter(
#     prefix="/todos",
#     tags=["todos"]
# )

# @router.post("/", response_model=TodoResponse)
# def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
#     """
#     Create a new todo item
#     """
#     try:
#         # Create a new todo object
#         #new_todo = Todo(**todo.dict())  # ✅ Corrected reference
#         new_todo = Todo(**todo.model_dump())
#         db.add(new_todo)
#         db.commit()
#         db.refresh(new_todo)
#         return new_todo

#     except SQLAlchemyError as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# @router.get("/", response_model=List[TodoResponse])
# def read_todos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     """
#     Retrieve a list of todo items
#     """
#     return db.query(Todo).offset(skip).limit(limit).all()

# @router.get("/{todo_id}", response_model=TodoResponse)
# def read_todo(todo_id: int, db: Session = Depends(get_db)):
#     """
#     Retrieve a specific todo item by ID
#     """
#     todo = db.query(Todo).filter(Todo.id == todo_id).first()
#     if todo is None:
#         raise HTTPException(status_code=404, detail="Todo not found")
#     return todo

# @router.put("/{todo_id}", response_model=TodoResponse)
# def update_todo(todo_id: int, todo: TodoUpdate, db: Session = Depends(get_db)):
#     """
#     Update a specific todo item
#     """
#     db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
#     if db_todo is None:
#         raise HTTPException(status_code=404, detail="Todo not found")
    
#     #update_data = todo.dict(exclude_unset=True)
#     update_data = todo.model_dump(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(db_todo, key, value)

#     try:
#         db.commit()
#         db.refresh(db_todo)
#         return db_todo
#     except SQLAlchemyError as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# @router.delete("/{todo_id}", response_model=TodoResponse)
# def delete_todo(todo_id: int, db: Session = Depends(get_db)):
#     """
#     Delete a specific todo item
#     """
#     db_todo = db.query(Todo).filter(Todo.id == todo_id).first()
#     if db_todo is None:
#         raise HTTPException(status_code=404, detail="Todo not found")
    
#     try:
#         db.delete(db_todo)
#         db.commit()
#         return db_todo
#     except SQLAlchemyError as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
