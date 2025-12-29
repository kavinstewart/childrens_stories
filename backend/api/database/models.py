"""SQLAlchemy ORM models for PostgreSQL."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Story(Base):
    """Story model - main entity for generated stories."""

    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    target_age_range: Mapped[str] = mapped_column(String(10), default="4-7")
    generation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    llm_model: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[Optional[str]] = mapped_column(Text)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    spread_count: Mapped[Optional[int]] = mapped_column(Integer)
    attempts: Mapped[Optional[int]] = mapped_column(Integer)
    is_illustrated: Mapped[bool] = mapped_column(Boolean, default=False)
    outline_json: Mapped[Optional[str]] = mapped_column(Text)
    judgment_json: Mapped[Optional[str]] = mapped_column(Text)
    progress_json: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    spreads: Mapped[list["StorySpread"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", order_by="StorySpread.spread_number"
    )
    character_references: Mapped[list["CharacterReference"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_stories_status", "status"),
        Index("idx_stories_created_at", "created_at"),
    )


class StorySpread(Base):
    """Story spread model - represents two facing pages."""

    __tablename__ = "story_spreads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stories.id", ondelete="CASCADE"), nullable=False
    )
    spread_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    was_revised: Mapped[bool] = mapped_column(Boolean, default=False)
    page_turn_note: Mapped[Optional[str]] = mapped_column(Text)
    illustration_prompt: Mapped[Optional[str]] = mapped_column(Text)
    illustration_path: Mapped[Optional[str]] = mapped_column(Text)

    # Relationship
    story: Mapped["Story"] = relationship(back_populates="spreads")

    __table_args__ = (
        Index("idx_story_spreads_story_id", "story_id"),
        # Unique constraint on story_id + spread_number
        Index("uq_story_spread", "story_id", "spread_number", unique=True),
    )


class CharacterReference(Base):
    """Character reference model - character sheets for illustrated stories."""

    __tablename__ = "character_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stories.id", ondelete="CASCADE"), nullable=False
    )
    character_name: Mapped[str] = mapped_column(String(100), nullable=False)
    character_description: Mapped[Optional[str]] = mapped_column(Text)
    reference_image_path: Mapped[Optional[str]] = mapped_column(Text)

    # Relationship
    story: Mapped["Story"] = relationship(back_populates="character_references")

    __table_args__ = (
        Index("idx_character_refs_story_id", "story_id"),
        Index("uq_character_ref", "story_id", "character_name", unique=True),
    )


class VLMEvaluation(Base):
    """VLM Judge evaluation records for optimization training data."""

    __tablename__ = "vlm_evaluations"

    id: Mapped[str] = mapped_column(String(8), primary_key=True)
    story_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("stories.id", ondelete="SET NULL")
    )
    spread_number: Mapped[Optional[int]] = mapped_column(Integer)

    # Input context
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    character_ref_paths: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    check_text_free: Mapped[bool] = mapped_column(Boolean, default=True)
    check_characters: Mapped[bool] = mapped_column(Boolean, default=True)
    check_composition: Mapped[bool] = mapped_column(Boolean, default=True)

    # VLM output
    vlm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    vlm_raw_response: Mapped[Optional[str]] = mapped_column(Text)
    vlm_overall_pass: Mapped[Optional[bool]] = mapped_column(Boolean)
    vlm_text_free: Mapped[Optional[bool]] = mapped_column(Boolean)
    vlm_character_match_score: Mapped[Optional[int]] = mapped_column(Integer)
    vlm_scene_accuracy_score: Mapped[Optional[int]] = mapped_column(Integer)
    vlm_composition_score: Mapped[Optional[int]] = mapped_column(Integer)
    vlm_style_score: Mapped[Optional[int]] = mapped_column(Integer)
    vlm_issues: Mapped[Optional[str]] = mapped_column(Text)  # JSON array

    # Human annotation
    human_verdict: Mapped[Optional[bool]] = mapped_column(Boolean)
    human_notes: Mapped[Optional[str]] = mapped_column(Text)
    annotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_vlm_evals_story_id", "story_id"),
        Index("idx_vlm_evals_unannotated", "human_verdict", postgresql_where=(human_verdict.is_(None))),
    )
