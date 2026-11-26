
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import Session
import pandas as pd

from backend.database import get_db
from backend.models import User, ChatSession, UploadedFile
from backend.routes.auth import get_current_user

from backend.services.file_service import (
    UPLOAD_DIR,
    ALLOWED_EXTENSIONS,
    extract_file_content
)
from backend.services.analytics_service import generate_analytics
from backend.services.dataset_service import get_dataset_analysis
from backend.services.chunking_service import create_chunks
from backend.services.document_service import store_document_chunks

router = APIRouter(prefix="/api/files", tags=["File Upload"])

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_file(
    session_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format"
        )

    chat_session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if not chat_session:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )

    stored_filename = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_filename

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )

        file_path.write_bytes(content)

        extracted_data = extract_file_content(file_path)

        row_count = extracted_data.get("row_count")

        uploaded_file = UploadedFile(
            session_id=session_id,
            filename=original_filename,
            stored_filename=stored_filename,
            file_type=extracted_data["file_type"],
            extension=extension,
            file_size=len(content),
            row_count=row_count
        )

        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)

        response = {
            "message": "File uploaded and processed successfully",
            "file_id": uploaded_file.id,
            "session_id": session_id,
            "filename": original_filename,
            "file_type": extracted_data["file_type"],
            "file_size": len(content)
        }

        if extracted_data["file_type"] == "tabular":
            dataset_analysis = get_dataset_analysis(file_path)
            response["analytics"] = dataset_analysis["analytics"]
            response["overview"] = dataset_analysis["overview"]

        elif extracted_data["file_type"] == "document":
            chunks = create_chunks(
                extracted_data,
                original_filename
            )

            if chunks:
                chunk_result = store_document_chunks(
                    chunks,
                    session_id=session_id,
                    uploaded_file_id=uploaded_file.id
                )
                response["chunking"] = chunk_result

        return response

    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise

    except Exception as error:
        db.rollback()
        file_path.unlink(missing_ok=True)

        if "uploaded_file" in locals() and uploaded_file.id:
            db.delete(uploaded_file)
            db.commit()

        raise HTTPException(
            status_code=422,
            detail=f"File processing failed: {str(error)}"
        )

    finally:
        await file.close()
