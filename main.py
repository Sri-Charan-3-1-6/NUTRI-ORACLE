import os
import json
import base64
import random
import io
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import google.generativeai as genai
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from PIL import Image

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    yield

app = FastAPI(
    title="NUTRI-ORACLE",
    description="The Oracle Sees What You Cannot",
    version="1.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data: https://fonts.googleapis.com https://fonts.gstatic.com;"
    return response

class AnalyzeRequest(BaseModel):
    ingredients: List[str] = Field(..., min_length=1, max_length=50)
    user_id: str = "guest"
    age: int = 25
    goal: str = "balanced"

class ImageRequest(BaseModel):
    image_base64: str
    user_id: str = "guest"

class OracleResponse(BaseModel):
    vitality_score: int
    deficiencies: List[str]
    health_risks: List[Dict[str, Any]]
    survival_recipes: List[Dict[str, Any]]
    body_timeline: Dict[str, str]
    meal_plan: Dict[str, Dict[str, Any]]
    oracle_verdict: str
    aura_color: str

@app.get("/health")
async def health_check():
    """Returns the health status of the service."""
    return {"status": "alive", "version": "1.0", "service": "nutri-oracle"}

@app.get("/quick-tip")
@limiter.limit("20/minute")
async def quick_tip(request: Request):
    """Returns a random health tip."""
    tips = [
        "Drink a glass of water immediately upon waking to jumpstart your organs.",
        "Your body needs healthy fats to absorb essential vitamins like A, D, E, and K.",
        "Chewing your food 30 times transforms digestion from a burden to a breeze.",
        "A lack of sleep makes your body crave carbs as a false energy source.",
        "Dark leafy greens are nature's multivitamins."
    ]
    return {"tip": random.choice(tips)}

@app.post("/analyze-ingredients", response_model=OracleResponse)
@limiter.limit("20/minute")
async def analyze_ingredients(request: Request, body: AnalyzeRequest):
    """Analyzes a list of ingredients and returns the Oracle's verdict."""
    if not body.ingredients:
        raise HTTPException(status_code=422, detail="Ingredients list cannot be empty")
        
    system_prompt = """You are NUTRI-ORACLE, a brutally honest nutritional intelligence system. Given a list of ingredients a person has at home, respond ONLY in valid JSON with NO markdown, NO explanation, exactly this structure:
{
  "vitality_score": integer 0-100 (overall diet health score),
  "deficiencies": array of strings (nutrients they are likely lacking based on these ingredients),
  "health_risks": array of objects each with {"risk": string, "severity": low/medium/high, "timeline": string like '30 days', "prevention": string},
  "survival_recipes": array of 3 objects each with {"name": string, "ingredients_used": array, "steps": array of strings, "health_benefit": string, "prep_time": string},
  "body_timeline": object with keys "7_days", "30_days", "6_months" each being a string describing body changes if eating only these foods,
  "meal_plan": object with keys "breakfast", "lunch", "dinner", "snack" each being object with {"meal": string, "ingredients_from_your_kitchen": array, "why": string},
  "oracle_verdict": one powerful sentence verdict on this person's current food situation (be dramatic and honest),
  "aura_color": single CSS hex color representing this diet energy (vibrant green for healthy, dark red for very unhealthy, orange for average)
}"""

    prompt = f"Ingredients: {', '.join(body.ingredients)}\nAge: {body.age}\nGoal: {body.goal}"

    try:
        if not os.getenv("GEMINI_API_KEY"):
            return get_mock_response()
            
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail="Oracle observation failed due to an interference in the connection.")

@app.post("/analyze-image", response_model=OracleResponse)
@limiter.limit("20/minute")
async def analyze_image(request: Request, body: ImageRequest):
    """Analyzes an image to find ingredients, then returns the Oracle's verdict."""
    try:
        if not os.getenv("GEMINI_API_KEY"):
            return get_mock_response()
            
        image_data = base64.b64decode(body.image_base64.split(",")[-1] if "," in body.image_base64 else body.image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        vision_model = genai.GenerativeModel('gemini-1.5-flash')
        vision_prompt = "List every food item you can see in this image. Return ONLY a JSON array of ingredient name strings, nothing else."
        vision_response = vision_model.generate_content([vision_prompt, image])
        
        ingredients_text = vision_response.text.strip()
        if ingredients_text.startswith("```json"):
            ingredients_text = ingredients_text[7:]
        if ingredients_text.startswith("```"):
            ingredients_text = ingredients_text[3:]
        if ingredients_text.endswith("```"):
            ingredients_text = ingredients_text[:-3]
            
        ingredients = json.loads(ingredients_text.strip())
        
        analyze_req = AnalyzeRequest(ingredients=ingredients[:50], user_id=body.user_id)
        return await analyze_ingredients(request, analyze_req)
    except Exception as e:
        raise HTTPException(status_code=500, detail="The Oracle could not decipher the visual offering.")

def get_mock_response():
    """Mock response for tests"""
    return {
        "vitality_score": 42,
        "deficiencies": ["Vitamin C", "Iron"],
        "health_risks": [{"risk": "Scurvy", "severity": "high", "timeline": "30 days", "prevention": "Eat citrus"}],
        "survival_recipes": [
            {"name": "Rice gruel", "ingredients_used": ["rice"], "steps": ["Boil water", "Add rice"], "health_benefit": "Basic calories", "prep_time": "20 mins"},
            {"name": "Water soup", "ingredients_used": ["water"], "steps": ["Boil"], "health_benefit": "Hydration", "prep_time": "5 mins"},
            {"name": "Lentil mush", "ingredients_used": ["lentils"], "steps": ["Cook"], "health_benefit": "Protein", "prep_time": "30 mins"}
        ],
        "body_timeline": {
            "7_days": "Fatigue sets in",
            "30_days": "Muscle loss begins",
            "6_months": "Bone density decreases"
        },
        "meal_plan": {
            "breakfast": {"meal": "Rice test", "ingredients_from_your_kitchen": ["rice"], "why": "energy"},
            "lunch": {"meal": "Lentils", "ingredients_from_your_kitchen": ["lentils"], "why": "protein"},
            "dinner": {"meal": "Spinach", "ingredients_from_your_kitchen": ["spinach"], "why": "iron"},
            "snack": {"meal": "Water", "ingredients_from_your_kitchen": [], "why": "hydration"}
        },
        "oracle_verdict": "A dark path awaits your nutritional journey.",
        "aura_color": "#ff3d3d"
    }

if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
