from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import cv2
import numpy as np
import json
from typing import List, Tuple

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, be specific.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCKUPS_DIR = os.path.join(BASE_DIR, "..", "mockups_db") # Store uploaded mockups here
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "generated_mockups")
DESIGNS_DIR = os.path.join(BASE_DIR, "..", "designs_db")
DATA_FILE = os.path.join(BASE_DIR, "data.json")

# Ensure directories exist
os.makedirs(MOCKUPS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DESIGNS_DIR, exist_ok=True)

# Mount static files to serve images
app.mount("/mockups", StaticFiles(directory=MOCKUPS_DIR), name="mockups")
app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")

# Data Models
class Point(BaseModel):
    x: float
    y: float

class MockupConfig(BaseModel):
    id: str
    name: str
    points: List[Point] # Top-left, Top-right, Bottom-right, Bottom-left

# Helper to load/save data
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"mockups": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.get("/")
def read_root():
    return {"message": "Mockup Generator API is running"}

@app.get("/mockups", response_model=List[MockupConfig])
def get_mockups():
    data = load_data()
    return data["mockups"]

@app.post("/upload-mockup")
async def upload_mockup(file: UploadFile = File(...)):
    file_path = os.path.join(MOCKUPS_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Initialize default config for this mockup if not exists
    data = load_data()
    # Check if exists
    existing = next((item for item in data["mockups"] if item["name"] == file.filename), None)
    
    if not existing:
        # Read image to determine dimensions
        img = cv2.imread(file_path)
        if img is not None:
            h, w = img.shape[:2]
            # Create a default box (50% of image size, centered)
            margin_x = w * 0.25
            margin_y = h * 0.25
            default_points = [
                {"x": margin_x, "y": margin_y},             # Top-left
                {"x": w - margin_x, "y": margin_y},         # Top-right
                {"x": w - margin_x, "y": h - margin_y},     # Bottom-right
                {"x": margin_x, "y": h - margin_y}          # Bottom-left
            ]
        else:
            # Fallback if image read fails
            default_points = [
                {"x": 100, "y": 100},
                {"x": 300, "y": 100},
                {"x": 300, "y": 300},
                {"x": 100, "y": 300}
            ]

        default_config = {
            "id": file.filename,
            "name": file.filename,
            "points": default_points
        }
        data["mockups"].append(default_config)
        save_data(data)
        
    return {"filename": file.filename, "url": f"/mockups/{file.filename}"}

@app.post("/save-config")
async def save_config(config: MockupConfig):
    data = load_data()
    for i, item in enumerate(data["mockups"]):
        if item["id"] == config.id:
            data["mockups"][i] = config.dict()
            save_data(data)
            return {"message": "Configuration saved"}
    
    # If not found, append
    data["mockups"].append(config.dict())
    save_data(data)
    return {"message": "Configuration created"}

# Helper for generation logic
def process_mockup_generation(mockup_id, design_content, design_filename):
    data = load_data()
    config = next((item for item in data["mockups"] if item["id"] == mockup_id), None)
    
    if not config:
        raise ValueError("Mockup config not found")

    mockup_path = os.path.join(MOCKUPS_DIR, config["name"])
    if not os.path.exists(mockup_path):
        raise ValueError("Mockup file not found")

    # Read images
    nparr = np.frombuffer(design_content, np.uint8)
    design_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    mockup_img = cv2.imread(mockup_path)
    
    if mockup_img is None or design_img is None:
         raise ValueError("Error loading images")

    h_design, w_design, _ = design_img.shape
    
    # Source points (corners of design)
    src_pts = np.array([
        [0, 0],
        [w_design - 1, 0],
        [w_design - 1, h_design - 1],
        [0, h_design - 1]
    ], dtype=np.float32)

    # Dest points from config
    dst_pts = np.array([
        [p["x"], p["y"]] for p in config["points"]
    ], dtype=np.float32)

    # Perspective Transform
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    
    # Warp Design
    warped_design = cv2.warpPerspective(
        design_img, 
        matrix, 
        (mockup_img.shape[1], mockup_img.shape[0]), 
        flags=cv2.INTER_LANCZOS4, 
        borderMode=cv2.BORDER_REPLICATE
    )
    
    # Generate Alpha Mask
    # Create a white image of the same size as the design to represent the alpha channel of the design plane
    mask_src = np.ones((h_design, w_design), dtype=np.uint8) * 255
    # Warp the mask using the same transform. This provides accurate anti-aliasing at the edges.
    warped_mask = cv2.warpPerspective(
        mask_src, 
        matrix, 
        (mockup_img.shape[1], mockup_img.shape[0]), 
        flags=cv2.INTER_LANCZOS4, 
        borderMode=cv2.BORDER_CONSTANT, 
        borderValue=0
    )
    
    # Alpha Blending
    # Convert to float for accurate blending
    bg_float = mockup_img.astype(np.float32)
    fg_float = warped_design.astype(np.float32)
    
    # Normalize mask to 0-1 and expand to 3 channels
    alpha = warped_mask.astype(np.float32) / 255.0
    alpha = np.clip(alpha, 0, 1) # Ensure range is [0, 1] after Lanczos
    alpha = np.dstack([alpha] * 3)
    
    # Standard alpha blending: Output = BG * (1 - Alpha) + FG * Alpha
    blended = bg_float * (1.0 - alpha) + fg_float * alpha
    final_result = np.clip(blended, 0, 255).astype(np.uint8)

    # Save output as WebP for smaller file sizes
    base_name = os.path.splitext(design_filename)[0].replace(' ', '_')
    config_base = os.path.splitext(config['name'])[0].replace(' ', '_')
    output_filename = f"{base_name}_{config_base}.webp"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    cv2.imwrite(output_path, final_result, [cv2.IMWRITE_WEBP_QUALITY, 90])
    
    return {
        "url": f"/generated/{output_filename}",
        "filename": output_filename
    }

@app.post("/generate")
async def generate(mockup_id: str = Form(...), design: UploadFile = File(...)):
    try:
        content = await design.read()
        return process_mockup_generation(mockup_id, content, design.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-bulk")
async def generate_bulk(mockup_id: str = Form(...), designs: List[UploadFile] = File(...)):
    results = []
    errors = []
    
    for design in designs:
        try:
            content = await design.read()
            res = process_mockup_generation(mockup_id, content, design.filename)
            results.append(res)
        except Exception as e:
            errors.append(f"Failed {design.filename}: {str(e)}")
            
    return {
        "results": results,
        "errors": errors,
        "count": len(results)
    }

@app.get("/generated-images")
def get_generated_images():
    images = []
    # Sort by modification time, newest first
    files = sorted(os.listdir(OUTPUT_DIR), key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    for filename in files:
        if filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            images.append({
                "filename": filename,
                "url": f"/generated/{filename}"
            })
    return images

from fastapi.responses import StreamingResponse
import io

@app.post("/preview")
async def preview(
    mockup_id: str = Form(...),
    points: str = Form(...),
    design: UploadFile = File(...)
):
    try:
        # Load Mockup Image (to get dimensions)
        data = load_data()
        config = next((item for item in data["mockups"] if item["id"] == mockup_id), None)
        if not config:
            raise HTTPException(status_code=404, detail="Mockup not found")
            
        mockup_path = os.path.join(MOCKUPS_DIR, config["name"])
        mockup_img = cv2.imread(mockup_path)
        if mockup_img is None:
            raise HTTPException(status_code=404, detail="Mockup file invalid")
            
        # Parse points
        # Expected JSON: [{"x":1, "y":2}, ...]
        pts_list = json.loads(points)
        dst_pts = np.array([
            [p["x"], p["y"]] for p in pts_list
        ], dtype=np.float32)
        
        # Load Design (from memory/upload)
        contents = await design.read()
        nparr = np.frombuffer(contents, np.uint8)
        design_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if design_img is None:
             raise HTTPException(status_code=400, detail="Invalid design image")
             
        # Process
        h_design, w_design, _ = design_img.shape
        src_pts = np.array([
            [0, 0],
            [w_design - 1, 0],
            [w_design - 1, h_design - 1],
            [0, h_design - 1]
        ], dtype=np.float32)
        
        # Warp
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        
        # Warped Design with better interpolation and replicated border
        warped_design = cv2.warpPerspective(
            design_img, 
            matrix, 
            (mockup_img.shape[1], mockup_img.shape[0]), 
            flags=cv2.INTER_LANCZOS4, 
            borderMode=cv2.BORDER_REPLICATE
        )
        
        # Soft Mask
        mask_src = np.ones((h_design, w_design), dtype=np.uint8) * 255
        warped_mask = cv2.warpPerspective(
            mask_src, 
            matrix, 
            (mockup_img.shape[1], mockup_img.shape[0]), 
            flags=cv2.INTER_LANCZOS4, 
            borderMode=cv2.BORDER_CONSTANT, 
            borderValue=0
        )
        
        # Clip mask
        warped_mask_u8 = np.clip(warped_mask, 0, 255).astype(np.uint8)
        
        # Alpha Blending (Same as generation)
        bg_float = mockup_img.astype(np.float32)
        fg_float = warped_design.astype(np.float32)
        
        alpha = warped_mask.astype(np.float32) / 255.0
        alpha = np.clip(alpha, 0, 1)
        alpha = np.dstack([alpha] * 3)
        
        blended = bg_float * (1.0 - alpha) + fg_float * alpha
        final_result = np.clip(blended, 0, 255).astype(np.uint8)
        
        # Encode as PNG
        _, encoded_img = cv2.imencode('.png', final_result)
        
        return StreamingResponse(io.BytesIO(encoded_img.tobytes()), media_type="image/png")
        
    except Exception as e:
        print(f"Preview Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
