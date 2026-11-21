"""Pydantic schemas for Phase 4 content strategy and caption generation."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    X = "x"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    THREADS = "threads"
    CUSTOM = "custom"


class ContentObjective(str, Enum):
    ENGAGEMENT = "engagement"
    BRAND_AWARENESS = "brand_awareness"
    EDUCATION = "education"
    PROMOTION = "promotion"
    STORYTELLING = "storytelling"
    COMMUNITY_BUILDING = "community_building"
    PRODUCT_SHOWCASE = "product_showcase"
    ENTERTAINMENT = "entertainment"
    PROFESSIONAL_COMMUNICATION = "professional_communication"
    CUSTOM = "custom"


class TargetAudience(str, Enum):
    GENERAL = "general"
    STUDENTS = "students"
    PROFESSIONALS = "professionals"
    CREATORS = "creators"
    CUSTOMERS = "customers"
    BUSINESS_OWNERS = "business_owners"
    CUSTOM = "custom"


class Tone(str, Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CONVERSATIONAL = "conversational"
    HUMOROUS = "humorous"
    INSPIRATIONAL = "inspirational"
    EDUCATIONAL = "educational"
    PERSUASIVE = "persuasive"
    MINIMALIST = "minimalist"
    STORYTELLING = "storytelling"
    CUSTOM = "custom"


class Language(str, Enum):
    ENGLISH = "english"
    KANNADA = "kannada"
    HINDI = "hindi"
    TAMIL = "tamil"
    TELUGU = "telugu"
    MALAYALAM = "malayalam"
    HINGLISH = "hinglish"
    CUSTOM = "custom"


class CaptionLength(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class EmojiPreference(str, Enum):
    NONE = "none"
    MINIMAL = "minimal"
    MODERATE = "moderate"
    EXPRESSIVE = "expressive"


class HashtagPreference(str, Enum):
    DISABLED = "disabled"
    MINIMAL = "minimal"
    RELEVANT = "relevant"
    CUSTOM = "custom"


class GenerationConfig(BaseModel):
    media_id: Optional[str] = None
    platform: Platform = Platform.INSTAGRAM
    objective: ContentObjective = ContentObjective.ENGAGEMENT
    audience: TargetAudience = TargetAudience.GENERAL
    custom_audience_description: Optional[str] = None
    tone: Tone = Tone.FRIENDLY
    custom_tone_description: Optional[str] = None
    language: Language = Language.ENGLISH
    custom_language_description: Optional[str] = None
    caption_length: CaptionLength = CaptionLength.MEDIUM
    emoji_preference: EmojiPreference = EmojiPreference.MINIMAL
    hashtag_preference: HashtagPreference = HashtagPreference.RELEVANT
    cta_enabled: bool = True
    brand_voice_description: Optional[str] = None
    brand_name: Optional[str] = None
    keywords_to_include: List[str] = Field(default_factory=list)
    words_or_claims_to_avoid: List[str] = Field(default_factory=list)
    additional_instructions: Optional[str] = None
    custom_platform_description: Optional[str] = None
    custom_objective_description: Optional[str] = None
    variant_count: int = Field(default=3, ge=1, le=5)

    @field_validator("keywords_to_include", "words_or_claims_to_avoid")
    @classmethod
    def clean_lists(cls, values: List[str]) -> List[str]:
        return list(dict.fromkeys(v.strip() for v in values if v and v.strip()))

    @model_validator(mode="after")
    def validate_custom_descriptions(self) -> "GenerationConfig":
        if self.platform == Platform.CUSTOM and not self.custom_platform_description:
            raise ValueError("custom_platform_description is required for a custom platform")
        if self.objective == ContentObjective.CUSTOM and not self.custom_objective_description:
            raise ValueError("custom_objective_description is required for a custom objective")
        if self.audience == TargetAudience.CUSTOM and not self.custom_audience_description:
            raise ValueError("custom_audience_description is required for a custom audience")
        if self.tone == Tone.CUSTOM and not self.custom_tone_description:
            raise ValueError("custom_tone_description is required for a custom tone")
        if self.language == Language.CUSTOM and not self.custom_language_description:
            raise ValueError("custom_language_description is required for a custom language")
        return self


class GenerationPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    main_content_angle: str
    key_message: str
    audience_relevance: str
    recommended_structure: List[str]
    tone_instructions: str
    platform_considerations: List[str]
    supported_facts: List[str]
    evidence_ids: List[str]
    prohibited_claims: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CaptionVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: str(uuid4()))
    approach: str
    caption_text: str
    platform: Platform
    tone: Tone
    content_angle: str
    hashtags: List[str] = Field(default_factory=list)
    cta: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    provider: str = ""
    model_id: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClaimClassification(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    NON_FACTUAL = "non_factual"


class GroundingClaim(BaseModel):
    claim: str
    classification: ClaimClassification
    evidence_ids: List[str] = Field(default_factory=list)
    explanation: str


class GroundingResult(BaseModel):
    grounding_id: str = Field(default_factory=lambda: str(uuid4()))
    status: str
    is_verified: bool
    claims: List[GroundingClaim] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    contradicted_claims: List[str] = Field(default_factory=list)
    correction_attempted: bool = False
    corrected_caption: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QualityResult(BaseModel):
    quality_id: str = Field(default_factory=lambda: str(uuid4()))
    grounding_separate_status: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    criteria: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GenerationRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    collection_id: str
    evidence_package_id: str
    evidence_package_version: int
    config: GenerationConfig
    plan: GenerationPlan
    variants: List[CaptionVariant] = Field(default_factory=list)
    grounding: Dict[str, GroundingResult] = Field(default_factory=dict)
    quality: Dict[str, QualityResult] = Field(default_factory=dict)
    provider: str = ""
    model_id: str = ""
    status: str = "complete"
    warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
