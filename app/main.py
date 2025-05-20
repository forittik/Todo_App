# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from routes import todo

# Initialize FastAPI app
app = FastAPI(
    title="Todo Application",
    description="A simple Todo API with FastAPI and MongoDB",
    version="1.0.0"
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for validation errors.
    Returns a detailed error response showing exactly what went wrong.
    """
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}

    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error["loc"]),  # Shows full field path
            "message": error["msg"],
            "input": body  # Shows user input for better debugging
        })

    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid request format",
            "message": "Your request contains invalid fields. Please check and correct them.",
            "validation_errors": errors
        },
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(todo.router)

# Optional health check endpoint
@app.get("/")
def health_check():
    return {"status": "healthy"}
