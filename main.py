from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import List
import os
from PIL import Image
from tempfile import NamedTemporaryFile
import subprocess  # For advanced compression tools

app = FastAPI()

# Settings
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "converted"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def optimize_webp(input_path: str, output_path: str, quality: int, method: int = 6):
    """
    Two-stage optimization:
    1. Convert to WebP with Pillow
    2. Further compress with cwebp (Google's official tool)
    """
    # Stage 1: Basic conversion
    img = Image.open(input_path)
    img.save(output_path, "webp", quality=quality, method=method)

    # Stage 2: Advanced compression (optional)
    if os.name != 'nt':  # Skip on Windows if cwebp not installed
        try:
            subprocess.run([
                "cwebp",
                "-q", str(quality),
                "-m", "6",  # Max compression
                "-pass", "10",  # Multi-pass analysis
                "-sharp_yuv",  # Better YUV conversion
                output_path, "-o", output_path
            ], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # Fallback to Pillow-only conversion


@app.post("/convert")
async def convert_files(
        files: List[UploadFile] = File(...),
        quality: int = 80,  # Default to balanced quality
        ultra_compress: bool = False  # Enable advanced compression
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []

    for file in files:
        if not file.filename.lower().endswith(".png"):
            results.append({
                "filename": file.filename,
                "success": False,
                "message": "Invalid file type (only PNG allowed)"
            })
            continue

        try:
            # Save uploaded file temporarily
            with NamedTemporaryFile(delete=False, suffix=".png", dir=UPLOAD_DIR) as temp_file:
                temp_path = temp_file.name
                temp_file.write(await file.read())

            output_filename = f"{len(os.listdir(OUTPUT_DIR)) + 1}.webp"
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            # Apply conversion + compression
            if ultra_compress:
                optimize_webp(temp_path, output_path, quality)
            else:
                Image.open(temp_path).save(output_path, "webp", quality=quality)

            # Get final file size
            file_size_kb = os.path.getsize(output_path) / 1024

            results.append({
                "filename": file.filename,
                "converted_filename": output_filename,
                "success": True,
                "message": "Conversion successful",
                "download_path": f"/download/{output_filename}",
                "file_size_kb": round(file_size_kb, 2),
                "compression_method": "cwebp" if ultra_compress else "pillow"
            })

            # Cleanup
            os.unlink(temp_path)

        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "message": f"Error processing file: {str(e)}"
            })

    return {"results": results}