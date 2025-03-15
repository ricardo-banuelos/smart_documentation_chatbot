from sqlalchemy.orm import Session
from sqlalchemy import exc
import os
import logging

from .models import Document, Session as DBSession, Message

logger = logging.getLogger(__name__)

def initialize_db():
    """
    Initialize the database and make sure it's ready for use.
    """
    try:
        logger.info("Initializing database...")
        # Database tables are created automatically when models.py is imported
        
        # Create upload directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        logger.info("Database initialization complete")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False

def cleanup_orphaned_files(db: Session):
    """
    Clean up any files in uploads directory that don't have a corresponding database entry.
    """
    try:
        # Get all file paths from database
        db_files = set(doc.file_path for doc in db.query(Document).all())
        
        # Get all files in uploads directory
        upload_dir = "uploads"
        if not os.path.exists(upload_dir):
            return
            
        actual_files = set(os.path.join(upload_dir, f) for f in os.listdir(upload_dir))
        
        # Find files that are in uploads but not in database
        orphaned_files = actual_files - db_files
        
        # Remove orphaned files
        for file_path in orphaned_files:
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Removed orphaned file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to remove orphaned file {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Error cleaning up orphaned files: {str(e)}")