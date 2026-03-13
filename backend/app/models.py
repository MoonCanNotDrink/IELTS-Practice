"""SQLAlchemy database models for IELTS Speaking practice."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey, Boolean
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """Authenticated user."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")


class Topic(Base):
    """Part 2 cue card topics."""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    points = Column(JSON, nullable=False)  # List of bullet points
    category = Column(String(100), default="general")  # e.g., "people", "places", "events"
    season = Column(String(20), default="2025-Q1")  # IELTS season
    created_at = Column(DateTime, default=datetime.utcnow)


class PracticeSession(Base):
    """A complete practice session (Part 1 + Part 2 + Part 3)."""
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Scores (filled after scoring)
    fluency_score = Column(Float, nullable=True)
    vocabulary_score = Column(Float, nullable=True)
    grammar_score = Column(Float, nullable=True)
    pronunciation_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)

    # AI feedback
    feedback = Column(Text, nullable=True)  # JSON string with detailed feedback
    sample_answer = Column(Text, nullable=True)  # Band 7+ sample answer

    # Relationships
    topic = relationship("Topic", backref="practice_sessions")
    user = relationship("User", back_populates="sessions")
    recordings = relationship("Recording", back_populates="session", cascade="all, delete-orphan")


class Recording(Base):
    """Individual audio recording for a part of the practice."""
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("practice_sessions.id"), nullable=False)
    part = Column(String(10), nullable=False)  # "part1", "part2", "part3"
    question_index = Column(Integer, default=0)  # Which question in the part
    question_text = Column(Text, nullable=True)  # The question asked

    # Audio file
    audio_filename = Column(String(255), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # ASR result
    transcript = Column(Text, nullable=True)
    word_timestamps = Column(JSON, nullable=True)  # [{word, start, end}, ...]

    # Pronunciation assessment
    pronunciation_accuracy = Column(Float, nullable=True)
    pronunciation_details = Column(JSON, nullable=True)  # Phoneme-level details

    # Notes (Part 2 preparation notes)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("PracticeSession", back_populates="recordings")
