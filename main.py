# uvicorn main:app --reload
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import List
import os
from PIL import Image
from tempfile import NamedTemporaryFile

app = FastAPI()

# Settings
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "converted"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Counter for incremental filenames
file_counter = 0


def get_next_filename():
    global file_counter
    file_counter += 1
    return f"{file_counter}.webp"


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "png"


@app.post("/convert")
async def convert_files(
        files: List[UploadFile] = File(...),
        quality: int = 100
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []

    for file in files:
        if not allowed_file(file.filename):
            results.append({
                "filename": file.filename,
                "success": False,
                "message": "Invalid file type (only PNG allowed)"
            })
            continue

        try:
            # Save uploaded file temporarily
            temp_file = NamedTemporaryFile(delete=False, suffix=".png", dir=UPLOAD_DIR)
            temp_path = temp_file.name
            with open(temp_path, "wb") as buffer:
                buffer.write(await file.read())

            # Get next incremental filename
            output_filename = get_next_filename()
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            # Convert to WebP
            img = Image.open(temp_path)
            img.save(output_path, "webp", quality=quality)

            results.append({
                "filename": file.filename,
                "converted_filename": output_filename,
                "success": True,
                "message": "Conversion successful",
                "download_path": f"/download/{output_filename}"
            })

            # Clean up temp file
            os.unlink(temp_path)

        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "message": f"Error processing file: {str(e)}"
            })

    return {"results": results}


@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="image/webp", filename=filename)
