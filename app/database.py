# app/database.py
from pymongo import MongoClient
from pymongo.collection import Collection
from bson import ObjectId
import certifi
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "mongodb+srv://{your-mongodb-key}@todoapp.epg3h.mongodb.net/?retryWrites=true&w=majority&appName=TodoAPP"
DATABASE_NAME = "todoapp"
COLLECTION_NAME = "todos"


client = None
db = None
todos_collection = None

def initialize_db():
    global client, db, todos_collection
    
    try:
        client = MongoClient(
            DATABASE_URL,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000  
        )

        client.admin.command('ping')
        logger.info("MongoDB connection successful!")
        
        db = client[DATABASE_NAME]
        todos_collection = db[COLLECTION_NAME]
  
        todos_collection.create_index("title")
        return True
        
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        client = None
        db = None
        todos_collection = None
        return False

initialize_db()


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


def get_db_collection():
    if todos_collection is None:
        if not initialize_db():
            raise Exception("MongoDB connection failed. Please check your connection settings.")
    return todos_collection
