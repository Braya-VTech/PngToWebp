from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import List
import os
from PIL import Image, ImageOps
from tempfile import NamedTemporaryFile

app = FastAPI()

# Settings
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "converted"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def smart_optimizer(input_path: str, output_path: str):
    """Auto-selects best compression based on image content"""
    img = Image.open(input_path)

    # Content detection (simple version)
    is_graphic = img.width < 500 and img.height < 500  # Likely icon/UI element

    if is_graphic:
        # Lossless for sharp graphics
        img.save(output_path, "webp", lossless=True, method=6)
    else:
        # Smart quality adjustment for photos
        quality = 85 - min(50, img.width * img.height // 100000)  # 85-35 based on size
        img.save(output_path, "webp", quality=max(65, quality), method=6)


@app.post("/convert")
async def convert_files(
        files: List[UploadFile] = File(...),
        mode: str = Form("auto")  # auto/quality/size
):
    results = []

    for file in files:
        try:
            # Temp file handling
            with NamedTemporaryFile(delete=False, suffix=".png", dir=UPLOAD_DIR) as temp_file:
                temp_path = temp_file.name
                await file.seek(0)
                temp_file.write(await file.read())

            output_filename = f"{len(os.listdir(OUTPUT_DIR)) + 1}.webp"
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            # Conversion logic
            if mode == "quality":
                Image.open(temp_path).save(output_path, "webp", quality=90, method=6)
            elif mode == "size":
                Image.open(temp_path).save(output_path, "webp", quality=65, method=6)
            else:  # auto
                smart_optimizer(temp_path, output_path)

            # Result metrics
            orig_size = os.path.getsize(temp_path) / 1024
            new_size = os.path.getsize(output_path) / 1024

            results.append({
                "filename": file.filename,
                "converted_filename": output_filename,
                "original_size_kb": round(orig_size, 2),
                "optimized_size_kb": round(new_size, 2),
                "compression_ratio": f"{100 - (new_size / orig_size) * 100:.1f}%",
                "download_path": f"/download/{output_filename}"
            })

            os.unlink(temp_path)

        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "message": str(e)
            })

    return {"results": results}