from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import cv2
import numpy as np
import json
from typing import List, Tuple, Optional

# Import naming engine
from naming_engine import (
    NamingEngine, 
    NamingConfig, 
    ValidationResult,
    load_naming_config, 
    save_naming_config
)

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
NAMING_CONFIG_FILE = os.path.join(BASE_DIR, "naming_config.json")

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
def process_mockup_generation(
    mockup_id: str, 
    design_content: bytes, 
    design_filename: str,
    naming_engine: Optional[NamingEngine] = None,
    batch_index: int = 0,
    batch_id: Optional[str] = None
):
    """
    Generate a mockup by placing a design onto a mockup template.
    
    Args:
        mockup_id: ID of the mockup configuration
        design_content: Raw bytes of the design image
        design_filename: Original filename of the design
        naming_engine: Optional NamingEngine for custom filenames
        batch_index: Index in batch operation (for bulk generation)
        batch_id: Batch identifier (for bulk generation)
    """
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
    mask_src = np.ones((h_design, w_design), dtype=np.uint8) * 255
    warped_mask = cv2.warpPerspective(
        mask_src, 
        matrix, 
        (mockup_img.shape[1], mockup_img.shape[0]), 
        flags=cv2.INTER_LANCZOS4, 
        borderMode=cv2.BORDER_CONSTANT, 
        borderValue=0
    )
    
    # Alpha Blending
    bg_float = mockup_img.astype(np.float32)
    fg_float = warped_design.astype(np.float32)
    
    alpha = warped_mask.astype(np.float32) / 255.0
    alpha = np.clip(alpha, 0, 1)
    alpha = np.dstack([alpha] * 3)
    
    blended = bg_float * (1.0 - alpha) + fg_float * alpha
    final_result = np.clip(blended, 0, 255).astype(np.uint8)

    # Generate filename using naming engine or fallback to default
    if naming_engine:
        output_filename = naming_engine.generate_filename(
            poster_content=design_content,
            poster_filename=design_filename,
            mockup_path=mockup_path,
            mockup_name=config['name'],
            batch_index=batch_index,
            batch_id=batch_id
        )
    else:
        # Fallback to simple naming with number padding
        import re
        def pad_single_digits(text):
            return re.sub(r'(?<!\d)(\d)(?!\d)', r'0\1', text)
        base_name = os.path.splitext(design_filename)[0].replace(' ', '_')
        config_base = os.path.splitext(config['name'])[0].replace(' ', '_')
        base_name = pad_single_digits(base_name)
        config_base = pad_single_digits(config_base)
        output_filename = f"{base_name}_{config_base}.webp"
    
    # Helper to save under 100KB
    def save_webp_under_limit(image, path, max_size=100*1024):
        quality = 90
        scale = 1.0
        current_img = image.copy()
        
        while True:
            # Encode
            _, buf = cv2.imencode('.webp', current_img, [cv2.IMWRITE_WEBP_QUALITY, quality])
            
            # Check size
            if len(buf) <= max_size:
                with open(path, "wb") as f:
                    f.write(buf)
                return
            
            # Reduce quality or resize
            quality -= 10
            if quality < 10:
                # Quality too low, resize instead
                scale *= 0.9
                h, w = current_img.shape[:2]
                new_h, new_w = int(h * 0.9), int(w * 0.9)
                if new_h < 50 or new_w < 50:
                    # Too small, just save whatever we have or break
                    # Saving last attempt
                    with open(path, "wb") as f:
                        f.write(buf)
                    return
                current_img = cv2.resize(current_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                quality = 80 # Reset quality for new size
            
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    save_webp_under_limit(final_result, output_path)
    
    return {
        "url": f"/generated/{output_filename}",
        "filename": output_filename
    }


@app.post("/generate")
async def generate(
    mockup_id: str = Form(...), 
    design: UploadFile = File(...),
    naming_template: Optional[str] = Form(None)
):
    """Generate a single mockup with optional custom naming template."""
    try:
        content = await design.read()
        
        # Set up naming engine if custom template provided
        naming_engine = None
        if naming_template:
            naming_config = load_naming_config(NAMING_CONFIG_FILE)
            naming_config.template = naming_template
            naming_engine = NamingEngine(naming_config)
        
        return process_mockup_generation(mockup_id, content, design.filename, naming_engine)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-bulk")
async def generate_bulk(
    mockup_id: str = Form(...), 
    designs: List[UploadFile] = File(...),
    naming_template: Optional[str] = Form(None)
):
    """Generate multiple mockups with optional custom naming template and collision handling."""
    results = []
    errors = []
    
    # Set up naming engine for consistent naming across batch
    naming_config = load_naming_config(NAMING_CONFIG_FILE)
    if naming_template:
        naming_config.template = naming_template
    naming_engine = NamingEngine(naming_config)
    naming_engine.reset_batch()  # Clear any previous batch state
    
    # Generate unique batch ID for this operation
    import hashlib
    from datetime import datetime
    batch_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
    
    for index, design in enumerate(designs):
        try:
            content = await design.read()
            res = process_mockup_generation(
                mockup_id, 
                content, 
                design.filename,
                naming_engine=naming_engine,
                batch_index=index,
                batch_id=batch_id
            )
            results.append(res)
        except Exception as e:
            errors.append(f"Failed {design.filename}: {str(e)}")
            
    return {
        "results": results,
        "errors": errors,
        "count": len(results),
        "batch_id": batch_id
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


# ============================================================================
# Naming Configuration Endpoints
# ============================================================================

@app.get("/naming-config")
def get_naming_config_endpoint():
    """Get the current naming configuration."""
    config = load_naming_config(NAMING_CONFIG_FILE)
    engine = NamingEngine(config)
    return {
        "config": config.model_dump(),
        "available_placeholders": engine.get_available_placeholders()
    }

@app.post("/naming-config")
def save_naming_config_endpoint(config: NamingConfig):
    """Save a new naming configuration."""
    # Validate the template first
    engine = NamingEngine(config)
    validation = engine.validate_template(config.template)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=validation.message)
    
    save_naming_config(config, NAMING_CONFIG_FILE)
    return {"message": "Naming configuration saved", "config": config.model_dump()}

@app.post("/validate-naming-template")
def validate_naming_template(template: str = Form(...)):
    """Validate a naming template and return details about placeholders."""
    engine = NamingEngine()
    result = engine.validate_template(template)
    return result.model_dump()

@app.get("/naming-preview")
def preview_naming(
    template: str = "{poster_name}_{mockup_name}",
    poster_name: str = "my_poster",
    mockup_name: str = "frame_mockup"
):
    """Preview what a filename would look like with the given template."""
    config = load_naming_config(NAMING_CONFIG_FILE)
    config.template = template
    engine = NamingEngine(config)
    preview = engine.preview_filename(template, poster_name, mockup_name)
    return {
        "preview": preview,
        "template": template
    }


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
