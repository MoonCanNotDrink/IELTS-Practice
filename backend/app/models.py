"""SQLAlchemy database models for IELTS practice."""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def utc_now() -> datetime:
    """Return a naive UTC timestamp for DB defaults and comparisons."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    """Authenticated user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    token_version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utc_now)

    sessions = relationship(
        "PracticeSession", back_populates="user", cascade="all, delete-orphan"
    )
    saved_topics = relationship(
        "SavedTopic", back_populates="user", cascade="all, delete-orphan"
    )
    writing_attempts = relationship(
        "WritingAttempt", back_populates="user", cascade="all, delete-orphan"
    )


class Topic(Base):
    """Part 2 cue card topics."""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    points = Column(JSON, nullable=False)
    category = Column(String(100), default="general")
    season = Column(String(20), default="2025-Q1")
    created_at = Column(DateTime, default=utc_now)


class PracticeSession(Base):
    """A complete practice session (Part 1 + Part 2 + Part 3)."""

    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=utc_now)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="in_progress")
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    fluency_score = Column(Float, nullable=True)
    vocabulary_score = Column(Float, nullable=True)
    grammar_score = Column(Float, nullable=True)
    pronunciation_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)

    feedback = Column(Text, nullable=True)
    sample_answer = Column(Text, nullable=True)

    topic = relationship("Topic", backref="practice_sessions")
    user = relationship("User", back_populates="sessions")
    recordings = relationship(
        "Recording", back_populates="session", cascade="all, delete-orphan"
    )


class Recording(Base):
    """Individual audio recording for a part of the practice."""

    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("practice_sessions.id"), nullable=False)
    part = Column(String(10), nullable=False)
    question_index = Column(Integer, default=0)
    question_text = Column(Text, nullable=True)

    audio_filename = Column(String(255), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    transcript = Column(Text, nullable=True)
    word_timestamps = Column(JSON, nullable=True)

    pronunciation_accuracy = Column(Float, nullable=True)
    pronunciation_details = Column(JSON, nullable=True)

    notes = Column(Text, nullable=True)
    prompt_match_type = Column(String(50), nullable=True)
    prompt_match_key = Column(String(255), nullable=True)
    prompt_source = Column(String(100), nullable=True)
    weakness_tags = Column(JSON, nullable=True)
    coaching_payload = Column(JSON, nullable=True)
    analysis_version = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    session = relationship("PracticeSession", back_populates="recordings")


class SavedTopic(Base):
    """User-scoped saved/custom topics."""

    __tablename__ = "saved_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    prompt_text = Column(Text, nullable=True)
    normalized_prompt = Column(Text, nullable=True)
    category = Column(String(100), default="general")
    source = Column(String(100), nullable=True)
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    is_archived = Column(Boolean, default=False)

    user = relationship("User", back_populates="saved_topics")


class PasswordResetToken(Base):
    """One-time password reset token for a user."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    requested_ip = Column(String(64), nullable=True)
    requested_user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", backref="password_reset_tokens")


class WritingPrompt(Base):
    __tablename__ = "writing_prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(120), unique=True, index=True, nullable=False)
    task_type = Column(String(20), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    prompt_text = Column(Text, nullable=False)
    prompt_details = Column(JSON, nullable=True)
    source = Column(String(50), default="seed")
    created_at = Column(DateTime, default=utc_now)

    attempts = relationship("WritingAttempt", back_populates="prompt")


class WritingAttempt(Base):
    __tablename__ = "writing_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    prompt_id = Column(Integer, ForeignKey("writing_prompts.id"), nullable=True)
    task_type = Column(String(20), nullable=False, index=True)

    prompt_title = Column(String(255), nullable=False)
    prompt_text = Column(Text, nullable=False)
    prompt_details = Column(JSON, nullable=True)
    essay_text = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)

    task_score = Column(Float, nullable=True)
    coherence_score = Column(Float, nullable=True)
    lexical_score = Column(Float, nullable=True)
    grammar_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)

    feedback = Column(Text, nullable=True)
    sample_answer = Column(Text, nullable=True)
    completed_at = Column(DateTime, default=utc_now, index=True)

    user = relationship("User", back_populates="writing_attempts")
    prompt = relationship("WritingPrompt", back_populates="attempts")
