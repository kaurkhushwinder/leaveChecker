"""SQLAlchemy models for users and uploaded leaf scans."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    """Represents an application user and owns uploaded scan records."""

    __tablename__ = "users"

    # Primary key used across user-related queries.
    id = Column(Integer, primary_key=True, index=True)
    # Display name captured during registration.
    name = Column(String, nullable=False)
    # Unique login identifier.
    email = Column(String, unique=True, index=True, nullable=False)
    # Stored password hash/string used for authentication.
    password = Column(String, nullable=False)

    # One user can have many leaf scan history entries.
    scans = relationship("LeafScan", back_populates="user")


class LeafScan(Base):
    """Stores one uploaded leaf image with prediction and guidance fields."""

    __tablename__ = "leaf_scans"

    # Unique scan ID for detail pages and history lookup.
    id = Column(Integer, primary_key=True, index=True)
    # Foreign key linking a scan to its owner.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Relative static file path of the uploaded image.
    image_path = Column(String, nullable=False)
    # Model-predicted disease class; can be null before inference finishes.
    disease_result = Column(String, nullable=True)
    # Recommended treatment text generated from prediction.
    treatment = Column(String, nullable=True)
    # UTC timestamp for sorting and timeline display.
    date = Column(DateTime, default=datetime.utcnow)

    # Back-reference to the owning User record.
    user = relationship("User", back_populates="scans")
