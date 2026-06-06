"""
File upload and management API endpoints.
"""

import os
import logging
import uuid
import mimetypes
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import FileResponse

from app.models.chat import FileResponse as FileResponseModel, FileStatus
from app.core.config import settings, get_upload_path
from data.supabase_chat import chat_db
from app.core.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed file types and extensions
ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.pdf'}
ALLOWED_MIME_TYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'application/vnd.ms-excel',  # .xls
    'text/csv',  # .csv
    'application/pdf',  # .pdf
}

def get_websocket_manager() -> ConnectionManager:
    """Get WebSocket manager dependency."""
    from app.main import manager
    return manager


@router.post("/files/upload/{session_id}", response_model=FileResponseModel)
async def upload_file(
    session_id: str,
    background_tasks: BackgroundTasks,
    websocket_manager: ConnectionManager = Depends(get_websocket_manager),
    file: UploadFile = File(...)
):
    """Upload a file to a chat session."""
    try:
        # Verify session exists
        session = chat_db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        contents = await file.read()
        file_size = len(contents)
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Generate unique filename to prevent conflicts
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = get_upload_path(session_id, unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = file.content_type
        
        # Validate MIME type
        if mime_type not in ALLOWED_MIME_TYPES:
            # Clean up file
            try:
                os.remove(file_path)
            except:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"MIME type not allowed: {mime_type}"
            )
        
        # Save to database
        file_record = chat_db.add_session_file(
            session_id=session_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type
        )
        
        # Notify via WebSocket
        await websocket_manager.send_file_update(
            session_id, file.filename, FileStatus.PROCESSING.value
        )
        
        # Schedule background processing
        background_tasks.add_task(
            process_uploaded_file, 
            file_record["id"], 
            file_path, 
            mime_type, 
            session_id,
            websocket_manager
        )
        
        return FileResponseModel(
            id=file_record["id"],
            session_id=file_record["session_id"],
            filename=file_record["filename"],
            file_path=file_record["file_path"],
            file_size=file_record["file_size"],
            mime_type=file_record["mime_type"],
            processing_status=FileStatus(file_record["processing_status"]),
            uploaded_at=file_record["uploaded_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/files/{session_id}", response_model=List[FileResponseModel])
async def list_session_files(session_id: str):
    """List all files for a chat session."""
    try:
        # Verify session exists
        session = chat_db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        files = chat_db.get_session_files(session_id)
        
        return [
            FileResponseModel(
                id=f["id"],
                session_id=f["session_id"],
                filename=f["filename"],
                file_path=f["file_path"],
                file_size=f["file_size"],
                mime_type=f["mime_type"],
                processing_status=FileStatus(f["processing_status"]),
                uploaded_at=f["uploaded_at"]
            )
            for f in files
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/files/{session_id}/{file_id}", response_model=FileResponseModel)
async def get_file_info(session_id: str, file_id: str):
    """Get information about a specific file."""
    try:
        # Verify session exists
        session = chat_db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        files = chat_db.get_session_files(session_id)
        file_record = next((f for f in files if f["id"] == file_id), None)
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponseModel(
            id=file_record["id"],
            session_id=file_record["session_id"],
            filename=file_record["filename"],
            file_path=file_record["file_path"],
            file_size=file_record["file_size"],
            mime_type=file_record["mime_type"],
            processing_status=FileStatus(file_record["processing_status"]),
            uploaded_at=file_record["uploaded_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file {file_id} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")


@router.get("/files/{session_id}/{file_id}/download")
async def download_file(session_id: str, file_id: str):
    """Download a file from a chat session."""
    try:
        # Verify session exists
        session = chat_db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        files = chat_db.get_session_files(session_id)
        file_record = next((f for f in files if f["id"] == file_id), None)
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = file_record["file_path"]
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(
            path=file_path,
            filename=file_record["filename"],
            media_type=file_record["mime_type"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.delete("/files/{session_id}/{file_id}")
async def delete_file(session_id: str, file_id: str):
    """Delete a file from a chat session."""
    try:
        # Verify session exists
        session = chat_db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        files = chat_db.get_session_files(session_id)
        file_record = next((f for f in files if f["id"] == file_id), None)
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete file from disk
        file_path = file_record["file_path"]
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from database (would need additional method in SupabaseChatDB)
        # For now, we'll update status to indicate deletion
        chat_db.update_file_status(file_id, "deleted")
        
        return {"message": "File deleted", "file_id": file_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


async def process_uploaded_file(file_id: str, file_path: str, mime_type: str, 
                              session_id: str, websocket_manager: ConnectionManager):
    """Process uploaded file in background."""
    try:
        logger.info(f"Processing file {file_id} at {file_path}")
        
        # Update status to processing
        chat_db.update_file_status(file_id, "processing")
        
        # File processing logic based on type
        if mime_type == "text/csv":
            await process_csv_file(file_path, session_id, websocket_manager)
        elif mime_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                          "application/vnd.ms-excel"]:
            await process_excel_file(file_path, session_id, websocket_manager)
        elif mime_type == "application/pdf":
            await process_pdf_file(file_path, session_id, websocket_manager)
        
        # Update status to processed
        chat_db.update_file_status(file_id, "processed")
        await websocket_manager.send_file_update(
            session_id, os.path.basename(file_path), FileStatus.PROCESSED.value
        )
        
        logger.info(f"Successfully processed file {file_id}")
        
    except Exception as e:
        logger.error(f"Error processing file {file_id}: {e}")
        
        # Update status to failed
        chat_db.update_file_status(file_id, "failed")
        await websocket_manager.send_file_update(
            session_id, os.path.basename(file_path), FileStatus.FAILED.value, error=str(e)
        )


async def process_csv_file(file_path: str, session_id: str, websocket_manager: ConnectionManager):
    """Process CSV file and extract information."""
    try:
        import pandas as pd
        
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Basic validation and info extraction
        info = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "sample_data": df.head(3).to_dict('records') if len(df) > 0 else []
        }
        
        logger.info(f"CSV file processed: {info}")
        
        # Could add more sophisticated processing here
        # For example, detect if it contains invoice data, validate format, etc.
        
    except Exception as e:
        logger.error(f"Error processing CSV file {file_path}: {e}")
        raise


async def process_excel_file(file_path: str, session_id: str, websocket_manager: ConnectionManager):
    """Process Excel file and extract information."""
    try:
        import pandas as pd
        
        # Read Excel file
        excel_file = pd.ExcelFile(file_path)
        sheets_info = {}
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheets_info[sheet_name] = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "sample_data": df.head(3).to_dict('records') if len(df) > 0 else []
            }
        
        logger.info(f"Excel file processed: {len(sheets_info)} sheets")
        
        # This is where you could integrate with existing Excel processing logic
        # from service/utilities.py if needed
        
    except Exception as e:
        logger.error(f"Error processing Excel file {file_path}: {e}")
        raise


async def process_pdf_file(file_path: str, session_id: str, websocket_manager: ConnectionManager):
    """Process PDF file and extract text."""
    try:
        # PDF processing would require additional libraries like PyPDF2 or pdfplumber
        # For now, just log that it was received
        
        file_size = os.path.getsize(file_path)
        logger.info(f"PDF file received: {file_size} bytes")
        
        # Could implement text extraction here for future use
        
    except Exception as e:
        logger.error(f"Error processing PDF file {file_path}: {e}")
        raise


# Cleanup endpoint for maintenance
@router.post("/files/maintenance/cleanup")
async def cleanup_orphaned_files(background_tasks: BackgroundTasks):
    """Clean up orphaned files (maintenance endpoint)."""
    try:
        def cleanup():
            # This would implement logic to clean up files for expired sessions
            # For now, just log the operation
            logger.info("File cleanup task executed")
        
        background_tasks.add_task(cleanup)
        return {"message": "File cleanup task scheduled"}
    except Exception as e:
        logger.error(f"Error scheduling file cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule cleanup: {str(e)}")