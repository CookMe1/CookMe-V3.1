from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Recipe(BaseModel):
    recipe_id: str
    user_id: str
    title: str
    description: str
    image: Optional[str] = None
    prep_time: str
    cook_time: str
    servings: int
    difficulty: str
    ingredients: List[dict]
    steps: List[str]
    tags: List[str]
    category: Optional[str] = None  # budget, student, instapot, quick, airfryer
    cuisine: Optional[str] = None  # Country/cuisine type: Italian, Mexican, Indian, etc.
    nutrition: Optional[dict] = None
    source_url: Optional[str] = None  # Original URL if imported
    likes_count: int = 0
    saves_count: int = 0
    hidden_by: List[str] = []  # List of user_ids who have "deleted" this recipe from their view
    favorited_by: List[str] = []  # List of user_ids who have favorited this recipe
    gallery_images: List[dict] = []  # List of images uploaded by users: [{user_id, image_url, uploaded_at}]
    uploader_id: Optional[str] = None  # User ID of the person who uploaded this recipe
    uploader_name: Optional[str] = None  # Display name of the uploader
    created_at: datetime
    updated_at: datetime

class RecipeCreate(BaseModel):
    title: str
    description: str
    image: Optional[str] = None
    prep_time: str
    cook_time: str
    servings: int
    difficulty: str
    ingredients: List[dict]
    steps: List[str]
    tags: List[str] = []
    category: Optional[str] = None
    cuisine: Optional[str] = None  # Country/cuisine type
    nutrition: Optional[dict] = None
    source_url: Optional[str] = None  # For URL/YouTube imports
    # Additional fields for imported recipes
    source: Optional[str] = None  # Source attribution
    instructions: Optional[str] = None  # Full instructions text
    confidence: Optional[str] = None  # Import confidence level
    confidence_score: Optional[float] = None
    needs_user_input: Optional[bool] = None
    is_video: Optional[bool] = None
    thumbnail_url: Optional[str] = None
    external_url_found: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Ignore extra fields not in model

class RecipeExtractRequest(BaseModel):
    image_urls: Optional[List[str]] = None
    recipe_url: Optional[str] = None


