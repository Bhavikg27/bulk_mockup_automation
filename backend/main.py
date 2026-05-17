from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import threading
import time
import uuid
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

try:
    from naming_engine import (
        NamingConfig,
        NamingEngine,
        load_naming_config,
        save_naming_config,
    )
except ModuleNotFoundError:
    from backend.naming_engine import (
        NamingConfig,
        NamingEngine,
        load_naming_config,
        save_naming_config,
    )

app = FastAPI(title="Mockup Studio V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MOCKUPS_DIR = os.path.join(ROOT_DIR, "mockups_db")
OUTPUT_DIR = os.path.join(ROOT_DIR, "generated_mockups")
DESIGNS_DIR = os.path.join(ROOT_DIR, "designs_db")
THUMBS_DIR = os.path.join(ROOT_DIR, "thumbs")
EXPORTS_DIR = os.path.join(ROOT_DIR, "exports")
TEMP_DIR = os.path.join(ROOT_DIR, "temp")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
DB_FILE = os.path.join(BASE_DIR, "mockup_studio.sqlite3")
NAMING_CONFIG_FILE = os.path.join(BASE_DIR, "naming_config.json")

for path in [MOCKUPS_DIR, OUTPUT_DIR, DESIGNS_DIR, THUMBS_DIR, EXPORTS_DIR, TEMP_DIR]:
    os.makedirs(path, exist_ok=True)

app.mount("/mockups", StaticFiles(directory=MOCKUPS_DIR), name="mockups")
app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")
app.mount("/designs", StaticFiles(directory=DESIGNS_DIR), name="designs")
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")


class Point(BaseModel):
    x: float
    y: float


class MockupConfig(BaseModel):
    id: str
    name: str
    points: List[Point]


class AssetUploadResult(BaseModel):
    id: str
    kind: str
    filename: str
    url: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    sha256: str


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def safe_filename(filename: str) -> str:
    base = os.path.basename(filename or "upload")
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", base).strip(" .")
    base = re.sub(r"\s+", " ", base)
    return base or f"upload-{uuid.uuid4().hex[:8]}"


def unique_path(folder: str, filename: str) -> str:
    filename = safe_filename(filename)
    stem, ext = os.path.splitext(filename)
    candidate = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{stem}_{counter:03d}{ext}")
        counter += 1
    return candidate


def unique_output_name(filename: str) -> str:
    filename = safe_filename(filename)
    stem, ext = os.path.splitext(filename)
    if not ext:
        ext = ".webp"
    candidate = f"{stem}{ext}"
    counter = 1
    while os.path.exists(os.path.join(OUTPUT_DIR, candidate)):
        candidate = f"{stem}_{counter:03d}{ext}"
        counter += 1
    return candidate


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def image_metadata_from_path(path: str) -> Dict[str, Optional[int]]:
    img = cv2.imread(path)
    if img is None:
        return {"width": None, "height": None}
    height, width = img.shape[:2]
    return {"width": int(width), "height": int(height)}


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                url TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mockup_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                points_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                percent INTEGER NOT NULL DEFAULT 0,
                stage TEXT NOT NULL DEFAULT 'queued',
                current_file TEXT,
                result_json TEXT NOT NULL DEFAULT '{}',
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                canceled_at TEXT
            );

            CREATE TABLE IF NOT EXISTS job_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                index_no INTEGER NOT NULL,
                filename TEXT NOT NULL,
                input_path TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL DEFAULT 'queued',
                percent INTEGER NOT NULL DEFAULT 0,
                output_filename TEXT,
                output_url TEXT,
                error TEXT,
                original_size INTEGER NOT NULL DEFAULT 0,
                output_size INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS outputs (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                item_id INTEGER,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                url TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                width INTEGER,
                height INTEGER,
                created_at TEXT NOT NULL
            );
            """
        )


def default_points_for_image(path: str) -> List[Dict[str, float]]:
    img = cv2.imread(path)
    if img is None:
        return [
            {"x": 100.0, "y": 100.0},
            {"x": 300.0, "y": 100.0},
            {"x": 300.0, "y": 300.0},
            {"x": 100.0, "y": 300.0},
        ]
    height, width = img.shape[:2]
    margin_x = width * 0.25
    margin_y = height * 0.25
    return [
        {"x": margin_x, "y": margin_y},
        {"x": width - margin_x, "y": margin_y},
        {"x": width - margin_x, "y": height - margin_y},
        {"x": margin_x, "y": height - margin_y},
    ]


def mirror_templates_to_data_json() -> None:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, name, points_json FROM mockup_templates ORDER BY created_at"
        ).fetchall()
    data = {
        "mockups": [
            {"id": row["id"], "name": row["name"], "points": json.loads(row["points_json"])}
            for row in rows
        ]
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def migrate_data_json() -> None:
    if not os.path.exists(DATA_FILE):
        return

    with db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS count FROM mockup_templates").fetchone()
        if existing and existing["count"] > 0:
            return

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("mockups", []):
            name = item.get("name") or item.get("id")
            if not name:
                continue
            path = os.path.join(MOCKUPS_DIR, name)
            points = item.get("points") or default_points_for_image(path)
            created = now_iso()
            conn.execute(
                """
                INSERT OR IGNORE INTO mockup_templates
                    (id, name, path, points_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("id") or name,
                    name,
                    path,
                    json.dumps(points),
                    created,
                    created,
                ),
            )


def load_data() -> Dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, name, points_json FROM mockup_templates ORDER BY created_at"
        ).fetchall()
    return {
        "mockups": [
            {"id": row["id"], "name": row["name"], "points": json.loads(row["points_json"])}
            for row in rows
        ]
    }


def save_data(data: Dict[str, Any]) -> None:
    created = now_iso()
    with db() as conn:
        for item in data.get("mockups", []):
            name = item["name"]
            conn.execute(
                """
                INSERT INTO mockup_templates
                    (id, name, path, points_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    path=excluded.path,
                    points_json=excluded.points_json,
                    updated_at=excluded.updated_at
                """,
                (
                    item["id"],
                    name,
                    os.path.join(MOCKUPS_DIR, name),
                    json.dumps(item["points"]),
                    created,
                    created,
                ),
            )
    mirror_templates_to_data_json()


def insert_asset(kind: str, filename: str, path: str, content_hash: str) -> Dict[str, Any]:
    meta = image_metadata_from_path(path)
    asset_id = uuid.uuid4().hex
    if kind == "design":
        url = f"/designs/{filename}"
    elif kind == "mockup":
        url = f"/mockups/{filename}"
    else:
        url = f"/generated/{filename}"

    created = now_iso()
    size_bytes = os.path.getsize(path)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO assets
                (id, kind, filename, path, url, size_bytes, sha256, width, height, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                kind,
                filename,
                path,
                url,
                size_bytes,
                content_hash,
                meta["width"],
                meta["height"],
                created,
            ),
        )
    return {
        "id": asset_id,
        "kind": kind,
        "filename": filename,
        "url": url,
        "size_bytes": size_bytes,
        "width": meta["width"],
        "height": meta["height"],
        "sha256": content_hash,
    }


def get_mockup_config(mockup_id: str) -> Dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT id, name, points_json FROM mockup_templates WHERE id=?",
            (mockup_id,),
        ).fetchone()
    if not row:
        raise ValueError("Mockup config not found")
    return {"id": row["id"], "name": row["name"], "points": json.loads(row["points_json"])}


def encode_webp_best_fit(
    image: np.ndarray,
    target_kb: Optional[int] = 100,
    quality: int = 90,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
) -> bytes:
    current = image.copy()

    if max_width or max_height:
        height, width = current.shape[:2]
        scale = 1.0
        if max_width and width > max_width:
            scale = min(scale, max_width / width)
        if max_height and height > max_height:
            scale = min(scale, max_height / height)
        if scale < 1:
            current = cv2.resize(
                current,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )

    if not target_kb:
        ok, buf = cv2.imencode(".webp", current, [cv2.IMWRITE_WEBP_QUALITY, int(quality)])
        if not ok:
            raise ValueError("Unable to encode WebP")
        return buf.tobytes()

    target_bytes = target_kb * 1024
    while True:
        best: Optional[bytes] = None
        low, high = 10, min(95, int(quality))
        while low <= high:
            mid = (low + high) // 2
            ok, buf = cv2.imencode(".webp", current, [cv2.IMWRITE_WEBP_QUALITY, mid])
            if not ok:
                raise ValueError("Unable to encode WebP")
            payload = buf.tobytes()
            if len(payload) <= target_bytes:
                best = payload
                low = mid + 1
            else:
                high = mid - 1

        if best:
            return best

        height, width = current.shape[:2]
        new_w = int(width * 0.9)
        new_h = int(height * 0.9)
        if new_w < 80 or new_h < 80:
            ok, buf = cv2.imencode(".webp", current, [cv2.IMWRITE_WEBP_QUALITY, 10])
            if not ok:
                raise ValueError("Unable to encode WebP")
            return buf.tobytes()
        current = cv2.resize(current, (new_w, new_h), interpolation=cv2.INTER_AREA)


def save_output_record(job_id: Optional[str], item_id: Optional[int], filename: str, path: str) -> None:
    meta = image_metadata_from_path(path)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO outputs
                (id, job_id, item_id, filename, path, url, size_bytes, width, height, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                job_id,
                item_id,
                filename,
                path,
                f"/generated/{filename}",
                os.path.getsize(path),
                meta["width"],
                meta["height"],
                now_iso(),
            ),
        )


def process_mockup_generation(
    mockup_id: str,
    design_content: bytes,
    design_filename: str,
    naming_engine: Optional[NamingEngine] = None,
    batch_index: int = 0,
    batch_id: Optional[str] = None,
    target_kb: int = 100,
    stage_callback=None,
) -> Dict[str, Any]:
    config = get_mockup_config(mockup_id)
    mockup_path = os.path.join(MOCKUPS_DIR, config["name"])
    if not os.path.exists(mockup_path):
        raise ValueError("Mockup file not found")

    if stage_callback:
        stage_callback("decoding")
    nparr = np.frombuffer(design_content, np.uint8)
    design_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    mockup_img = cv2.imread(mockup_path)
    if mockup_img is None or design_img is None:
        raise ValueError("Error loading images")

    if stage_callback:
        stage_callback("rendering")
    h_design, w_design, _ = design_img.shape
    src_pts = np.array(
        [[0, 0], [w_design - 1, 0], [w_design - 1, h_design - 1], [0, h_design - 1]],
        dtype=np.float32,
    )
    dst_pts = np.array([[p["x"], p["y"]] for p in config["points"]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

    warped_design = cv2.warpPerspective(
        design_img,
        matrix,
        (mockup_img.shape[1], mockup_img.shape[0]),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REPLICATE,
    )
    mask_src = np.ones((h_design, w_design), dtype=np.uint8) * 255
    warped_mask = cv2.warpPerspective(
        mask_src,
        matrix,
        (mockup_img.shape[1], mockup_img.shape[0]),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    bg_float = mockup_img.astype(np.float32)
    fg_float = warped_design.astype(np.float32)
    alpha = np.clip(warped_mask.astype(np.float32) / 255.0, 0, 1)
    alpha = np.dstack([alpha] * 3)
    final_result = np.clip(bg_float * (1.0 - alpha) + fg_float * alpha, 0, 255).astype(np.uint8)

    if naming_engine:
        output_filename = naming_engine.generate_filename(
            poster_content=design_content,
            poster_filename=design_filename,
            mockup_path=mockup_path,
            mockup_name=config["name"],
            batch_index=batch_index,
            batch_id=batch_id,
        )
    else:
        stem = os.path.splitext(design_filename)[0].replace(" ", "_")
        mockup_stem = os.path.splitext(config["name"])[0].replace(" ", "_")
        output_filename = f"{stem}_{mockup_stem}.webp"

    output_filename = unique_output_name(output_filename)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    if stage_callback:
        stage_callback("optimizing")
    payload = encode_webp_best_fit(final_result, target_kb=target_kb, quality=90)

    if stage_callback:
        stage_callback("saving")
    with open(output_path, "wb") as f:
        f.write(payload)

    return {
        "url": f"/generated/{output_filename}",
        "filename": output_filename,
        "size_bytes": os.path.getsize(output_path),
    }


def update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = now_iso()
    assignments = ", ".join([f"{key}=?" for key in fields])
    values = list(fields.values()) + [job_id]
    with db() as conn:
        conn.execute(f"UPDATE jobs SET {assignments} WHERE id=?", values)


def update_item(item_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = now_iso()
    assignments = ", ".join([f"{key}=?" for key in fields])
    values = list(fields.values()) + [item_id]
    with db() as conn:
        conn.execute(f"UPDATE job_items SET {assignments} WHERE id=?", values)


def is_job_canceled(job_id: str) -> bool:
    with db() as conn:
        row = conn.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    return bool(row and row["status"] == "canceled")


def recompute_job_progress(job_id: str, stage: str, current_file: Optional[str]) -> Dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed,
                SUM(percent) AS progress_sum
            FROM job_items
            WHERE job_id=?
            """,
            (job_id,),
        ).fetchone()
    total = int(row["total"] or 0)
    completed = int(row["completed"] or 0)
    failed = int(row["failed"] or 0)
    progress_sum = int(row["progress_sum"] or 0)
    percent = int(round(progress_sum / total)) if total else 0
    update_job(
        job_id,
        total=total,
        completed=completed,
        failed=failed,
        percent=percent,
        stage=stage,
        current_file=current_file,
    )
    return {"total": total, "completed": completed, "failed": failed, "percent": percent}


def run_mockup_job(job_id: str, mockup_id: str, naming_template: Optional[str], target_kb: int) -> None:
    started = now_iso()
    update_job(job_id, status="running", stage="queued", started_at=started)

    naming_config = load_naming_config(NAMING_CONFIG_FILE)
    if naming_template:
        naming_config.template = naming_template
    naming_engine = NamingEngine(naming_config)
    naming_engine.reset_batch()
    batch_id = job_id[:6]

    with db() as conn:
        items = conn.execute(
            "SELECT * FROM job_items WHERE job_id=? ORDER BY index_no",
            (job_id,),
        ).fetchall()

    for item in items:
        if is_job_canceled(job_id):
            update_item(item["id"], status="canceled", stage="canceled")
            continue

        item_id = int(item["id"])
        filename = item["filename"]
        update_item(item_id, status="running", stage="decoding", percent=5)
        recompute_job_progress(job_id, "decoding", filename)

        def stage_callback(stage: str) -> None:
            stage_percent = {
                "decoding": 15,
                "rendering": 45,
                "optimizing": 75,
                "saving": 90,
            }.get(stage, 10)
            update_item(item_id, stage=stage, percent=stage_percent)
            recompute_job_progress(job_id, stage, filename)

        try:
            with open(item["input_path"], "rb") as f:
                content = f.read()
            result = process_mockup_generation(
                mockup_id=mockup_id,
                design_content=content,
                design_filename=filename,
                naming_engine=naming_engine,
                batch_index=int(item["index_no"]),
                batch_id=batch_id,
                target_kb=target_kb,
                stage_callback=stage_callback,
            )
            output_path = os.path.join(OUTPUT_DIR, result["filename"])
            save_output_record(job_id, item_id, result["filename"], output_path)
            update_item(
                item_id,
                status="done",
                stage="done",
                percent=100,
                output_filename=result["filename"],
                output_url=result["url"],
                output_size=result["size_bytes"],
            )
        except Exception as exc:
            update_item(item_id, status="failed", stage="failed", percent=100, error=str(exc))

        recompute_job_progress(job_id, "saving", filename)

    progress = recompute_job_progress(job_id, "done", None)
    status = "completed"
    if is_job_canceled(job_id):
        status = "canceled"
    elif progress["failed"] and progress["completed"] == 0:
        status = "failed"
    elif progress["failed"]:
        status = "completed_with_errors"

    update_job(job_id, status=status, stage=status, percent=100, finished_at=now_iso())


def run_optimizer_job(job_id: str, target_kb: int, quality: int, max_width: Optional[int], max_height: Optional[int]) -> None:
    update_job(job_id, status="running", stage="queued", started_at=now_iso())
    with db() as conn:
        items = conn.execute(
            "SELECT * FROM job_items WHERE job_id=? ORDER BY index_no",
            (job_id,),
        ).fetchall()

    for item in items:
        if is_job_canceled(job_id):
            update_item(item["id"], status="canceled", stage="canceled")
            continue

        item_id = int(item["id"])
        filename = item["filename"]
        try:
            update_item(item_id, status="running", stage="decoding", percent=10)
            recompute_job_progress(job_id, "decoding", filename)
            img = cv2.imread(item["input_path"], cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Unsupported image for backend optimizer")

            update_item(item_id, stage="optimizing", percent=70)
            recompute_job_progress(job_id, "optimizing", filename)
            payload = encode_webp_best_fit(
                img,
                target_kb=target_kb,
                quality=quality,
                max_width=max_width,
                max_height=max_height,
            )

            output_filename = unique_output_name(f"{os.path.splitext(filename)[0]}.webp")
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            with open(output_path, "wb") as f:
                f.write(payload)
            save_output_record(job_id, item_id, output_filename, output_path)
            update_item(
                item_id,
                status="done",
                stage="done",
                percent=100,
                output_filename=output_filename,
                output_url=f"/generated/{output_filename}",
                output_size=os.path.getsize(output_path),
            )
        except Exception as exc:
            update_item(item_id, status="failed", stage="failed", percent=100, error=str(exc))
        recompute_job_progress(job_id, "saving", filename)

    progress = recompute_job_progress(job_id, "done", None)
    status = "completed_with_errors" if progress["failed"] else "completed"
    if is_job_canceled(job_id):
        status = "canceled"
    update_job(job_id, status=status, stage=status, percent=100, finished_at=now_iso())


def create_job(kind: str, files: List[UploadFile]) -> str:
    job_id = uuid.uuid4().hex
    created = now_iso()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO jobs
                (id, kind, status, total, completed, failed, percent, stage, created_at, updated_at)
            VALUES (?, ?, 'queued', ?, 0, 0, 0, 'queued', ?, ?)
            """,
            (job_id, kind, len(files), created, created),
        )
    return job_id


def job_payload(job_id: str) -> Dict[str, Any]:
    with db() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        items = conn.execute(
            "SELECT * FROM job_items WHERE job_id=? ORDER BY index_no",
            (job_id,),
        ).fetchall()
    payload = dict(job)
    payload["items"] = [dict(item) for item in items]
    return payload


async def store_job_uploads(job_id: str, files: List[UploadFile]) -> None:
    with db() as conn:
        for index, upload in enumerate(files):
            content = await upload.read()
            filename = safe_filename(upload.filename)
            input_path = unique_path(TEMP_DIR, f"{job_id}_{index:03d}_{filename}")
            with open(input_path, "wb") as f:
                f.write(content)
            created = now_iso()
            conn.execute(
                """
                INSERT INTO job_items
                    (job_id, index_no, filename, input_path, status, stage, percent,
                     original_size, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'queued', 'queued', 0, ?, ?, ?)
                """,
                (job_id, index, filename, input_path, len(content), created, created),
            )


init_db()
migrate_data_json()


@app.get("/")
def read_root():
    return {"message": "Mockup Studio V2 API is running"}


@app.get("/mockups", response_model=List[MockupConfig])
def get_mockups():
    return load_data()["mockups"]


@app.post("/upload-mockup")
async def upload_mockup(file: UploadFile = File(...)):
    content = await file.read()
    file_path = unique_path(MOCKUPS_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    filename = os.path.basename(file_path)
    points = default_points_for_image(file_path)
    created = now_iso()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO mockup_templates
                (id, name, path, points_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (filename, filename, file_path, json.dumps(points), created, created),
        )
    insert_asset("mockup", filename, file_path, sha256_bytes(content))
    mirror_templates_to_data_json()
    return {"filename": filename, "url": f"/mockups/{filename}"}


@app.post("/save-config")
async def save_config(config: MockupConfig):
    points = [point.model_dump() for point in config.points]
    created = now_iso()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO mockup_templates
                (id, name, path, points_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                path=excluded.path,
                points_json=excluded.points_json,
                updated_at=excluded.updated_at
            """,
            (
                config.id,
                config.name,
                os.path.join(MOCKUPS_DIR, config.name),
                json.dumps(points),
                created,
                created,
            ),
        )
    mirror_templates_to_data_json()
    return {"message": "Configuration saved"}


@app.post("/api/assets", response_model=List[AssetUploadResult])
async def upload_assets(kind: str = Form("design"), files: List[UploadFile] = File(...)):
    if kind not in {"design", "mockup"}:
        raise HTTPException(status_code=400, detail="kind must be design or mockup")
    folder = DESIGNS_DIR if kind == "design" else MOCKUPS_DIR
    results = []
    for upload in files:
        content = await upload.read()
        path = unique_path(folder, upload.filename)
        with open(path, "wb") as f:
            f.write(content)
        filename = os.path.basename(path)
        results.append(insert_asset(kind, filename, path, sha256_bytes(content)))
    return results


@app.get("/api/assets")
def list_assets(kind: Optional[str] = None):
    query = "SELECT * FROM assets"
    params: List[Any] = []
    if kind:
        query += " WHERE kind=?"
        params.append(kind)
    query += " ORDER BY created_at DESC"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@app.post("/generate")
async def generate(
    mockup_id: str = Form(...),
    design: UploadFile = File(...),
    naming_template: Optional[str] = Form(None),
):
    try:
        content = await design.read()
        naming_engine = None
        if naming_template:
            naming_config = load_naming_config(NAMING_CONFIG_FILE)
            naming_config.template = naming_template
            naming_engine = NamingEngine(naming_config)
        result = process_mockup_generation(mockup_id, content, design.filename, naming_engine)
        save_output_record(None, None, result["filename"], os.path.join(OUTPUT_DIR, result["filename"]))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-bulk")
async def generate_bulk(
    mockup_id: str = Form(...),
    designs: List[UploadFile] = File(...),
    naming_template: Optional[str] = Form(None),
):
    job = await create_mockup_job(mockup_id, designs, naming_template, 100)
    return job


@app.post("/api/jobs/mockup-batch")
async def create_mockup_job(
    mockup_id: str = Form(...),
    designs: List[UploadFile] = File(...),
    naming_template: Optional[str] = Form(None),
    target_kb: int = Form(100),
):
    try:
        get_mockup_config(mockup_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    job_id = create_job("mockup_batch", designs)
    await store_job_uploads(job_id, designs)
    thread = threading.Thread(
        target=run_mockup_job,
        args=(job_id, mockup_id, naming_template, target_kb),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id, "job": job_payload(job_id)}


@app.post("/api/jobs/optimize-batch")
async def create_optimizer_job(
    images: List[UploadFile] = File(...),
    target_kb: int = Form(100),
    quality: int = Form(90),
    max_width: Optional[int] = Form(None),
    max_height: Optional[int] = Form(None),
):
    job_id = create_job("optimize_batch", images)
    await store_job_uploads(job_id, images)
    thread = threading.Thread(
        target=run_optimizer_job,
        args=(job_id, target_kb, quality, max_width, max_height),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id, "job": job_payload(job_id)}


@app.get("/api/jobs")
def list_jobs(limit: int = 20):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return job_payload(job_id)


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    update_job(job_id, status="canceled", stage="canceled", canceled_at=now_iso())
    return job_payload(job_id)


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    async def event_stream():
        last_payload = ""
        while True:
            payload = job_payload(job_id)
            encoded = json.dumps(payload, default=str)
            if encoded != last_payload:
                yield f"data: {encoded}\n\n"
                last_payload = encoded
            if payload["status"] in {"completed", "completed_with_errors", "failed", "canceled"}:
                break
            await asyncio.sleep(0.35)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/generated-images")
def get_generated_images():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM outputs ORDER BY created_at DESC LIMIT 500"
        ).fetchall()

    seen = {row["filename"] for row in rows}
    images = [dict(row) for row in rows]
    files = sorted(
        os.listdir(OUTPUT_DIR),
        key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)),
        reverse=True,
    )
    for filename in files:
        if filename in seen or not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        path = os.path.join(OUTPUT_DIR, filename)
        images.append(
            {
                "filename": filename,
                "url": f"/generated/{filename}",
                "size_bytes": os.path.getsize(path),
                "created_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
            }
        )
    return images


@app.get("/api/exports/{job_id}/download")
def download_job_zip(job_id: str):
    payload = job_payload(job_id)
    ready_items = [
        item for item in payload["items"] if item["status"] == "done" and item["output_filename"]
    ]
    if not ready_items:
        raise HTTPException(status_code=404, detail="No completed outputs for this job")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = []
        for item in ready_items:
            path = os.path.join(OUTPUT_DIR, item["output_filename"])
            if not os.path.exists(path):
                continue
            zf.write(path, arcname=item["output_filename"])
            manifest.append(
                {
                    "source": item["filename"],
                    "output": item["output_filename"],
                    "size_bytes": item["output_size"],
                    "url": item["output_url"],
                }
            )
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="mockup-job-{job_id[:8]}.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@app.get("/naming-config")
def get_naming_config_endpoint():
    config = load_naming_config(NAMING_CONFIG_FILE)
    engine = NamingEngine(config)
    return {"config": config.model_dump(), "available_placeholders": engine.get_available_placeholders()}


@app.post("/naming-config")
def save_naming_config_endpoint(config: NamingConfig):
    engine = NamingEngine(config)
    validation = engine.validate_template(config.template)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=validation.message)
    save_naming_config(config, NAMING_CONFIG_FILE)
    return {"message": "Naming configuration saved", "config": config.model_dump()}


@app.post("/validate-naming-template")
def validate_naming_template(template: str = Form(...)):
    engine = NamingEngine()
    result = engine.validate_template(template)
    return result.model_dump()


@app.get("/naming-preview")
def preview_naming(
    template: str = "{poster_name}_{mockup_name}",
    poster_name: str = "my_poster",
    mockup_name: str = "frame_mockup",
):
    config = load_naming_config(NAMING_CONFIG_FILE)
    config.template = template
    engine = NamingEngine(config)
    return {"preview": engine.preview_filename(template, poster_name, mockup_name), "template": template}


@app.post("/preview")
async def preview(
    mockup_id: str = Form(...),
    points: str = Form(...),
    design: UploadFile = File(...),
):
    try:
        config = get_mockup_config(mockup_id)
        mockup_path = os.path.join(MOCKUPS_DIR, config["name"])
        mockup_img = cv2.imread(mockup_path)
        if mockup_img is None:
            raise HTTPException(status_code=404, detail="Mockup file invalid")

        pts_list = json.loads(points)
        dst_pts = np.array([[p["x"], p["y"]] for p in pts_list], dtype=np.float32)

        contents = await design.read()
        nparr = np.frombuffer(contents, np.uint8)
        design_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if design_img is None:
            raise HTTPException(status_code=400, detail="Invalid design image")

        h_design, w_design, _ = design_img.shape
        src_pts = np.array(
            [[0, 0], [w_design - 1, 0], [w_design - 1, h_design - 1], [0, h_design - 1]],
            dtype=np.float32,
        )

        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped_design = cv2.warpPerspective(
            design_img,
            matrix,
            (mockup_img.shape[1], mockup_img.shape[0]),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_REPLICATE,
        )
        mask_src = np.ones((h_design, w_design), dtype=np.uint8) * 255
        warped_mask = cv2.warpPerspective(
            mask_src,
            matrix,
            (mockup_img.shape[1], mockup_img.shape[0]),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        alpha = np.clip(warped_mask.astype(np.float32) / 255.0, 0, 1)
        alpha = np.dstack([alpha] * 3)
        final_result = np.clip(
            mockup_img.astype(np.float32) * (1.0 - alpha) + warped_design.astype(np.float32) * alpha,
            0,
            255,
        ).astype(np.uint8)

        ok, encoded_img = cv2.imencode(".png", final_result)
        if not ok:
            raise ValueError("Preview encoding failed")
        return StreamingResponse(io.BytesIO(encoded_img.tobytes()), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
