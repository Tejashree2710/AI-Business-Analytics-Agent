
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
from uuid import uuid4
import pandas as pd

from backend.services.file_service import (
    UPLOAD_DIR,
    ALLOWED_EXTENSIONS,
    extract_file_content
)
from backend.services.analytics_service import generate_analytics

router = APIRouter(prefix="/api/files", tags=["File Upload"])

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format"
        )

    unique_name = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / unique_name

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )

        file_path.write_bytes(content)

        extracted_data = extract_file_content(file_path)

        response = {
            "message": "File uploaded and processed successfully",
            "filename": file.filename,
            "file_type": extracted_data["file_type"],
            "extracted_data": extracted_data
        }

        if extracted_data["file_type"] == "tabular":
            df = pd.DataFrame(extracted_data["data"])
            response["analytics"] = generate_analytics(df)

        return response

    except HTTPException:
        raise

    except Exception as error:
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=422,
            detail=f"File processing failed: {str(error)}"
        )
