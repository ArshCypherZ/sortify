from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from pathlib import Path
import json

class FileIndex(SQLModel, table=True):
    file_hash: str = Field(primary_key=True, index=True, description="SHA-256 hash of the file content")
    last_seen: datetime = Field(default_factory=datetime.now)
    current_path: str = Field(index=True)
    status: str = Field(default="processed")
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None

class Transaction(SQLModel, table=True):
    id: str = Field(primary_key=True)
    src_path: str
    dest_path: str
    action_type: str
    status: str = Field(default="pending")
    timestamp: datetime = Field(default_factory=datetime.now)
    rollback_data_json: str = Field(default="{}")
    
    @property
    def rollback_data(self) -> dict:
        return json.loads(self.rollback_data_json)
    
    @rollback_data.setter
    def rollback_data(self, value: dict):
        self.rollback_data_json = json.dumps(value)

class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_hash: str = Field(index=True, foreign_key="fileindex.file_hash")
    original_category: str
    corrected_category: str
    confidence_score: float
    timestamp: datetime = Field(default_factory=datetime.now)
