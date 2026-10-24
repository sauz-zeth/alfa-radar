import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from back.core.constants import (
    DEFAULT_BUSINESS_NAME,
    DEFAULT_ENTREPRENEUR_NAME,
    CounterpartyDirection,
    Impact,
    OnboardingStep,
    Role,
)
from back.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    uid: Mapped[str] = mapped_column(String(32), primary_key=True)
    org_type: Mapped[str | None] = mapped_column(String(64))
    okfs_name: Mapped[str | None] = mapped_column(String(128))
    company_age_years_gradation: Mapped[str | None] = mapped_column(String(32))
    eco_mark_label: Mapped[str | None] = mapped_column(String(64))
    main_okved_code: Mapped[str | None] = mapped_column(String(16), index=True)
    main_okved_name: Mapped[str | None] = mapped_column(Text)
    negative_mark: Mapped[float | None] = mapped_column(Float)
    amount_workers_fns_gradation: Mapped[str | None] = mapped_column(String(64))
    amount_workers_spark_gradation: Mapped[str | None] = mapped_column(String(64))
    client_type: Mapped[str | None] = mapped_column(String(32))
    cl_product_rko_mark: Mapped[bool] = mapped_column(Boolean, default=False)
    cl_product_gar_mark: Mapped[bool] = mapped_column(Boolean, default=False)
    cl_product_loa_mark: Mapped[bool] = mapped_column(Boolean, default=False)
    cl_product_lea_mark: Mapped[bool] = mapped_column(Boolean, default=False)
    cl_product_dep_mark: Mapped[bool] = mapped_column(Boolean, default=False)
    cl_product_zpp_mark: Mapped[bool] = mapped_column(Boolean, default=False)
    fts_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    fts_country_name: Mapped[str | None] = mapped_column(String(128))
    factoring_mark: Mapped[bool] = mapped_column(Boolean, default=False)
    revenue: Mapped[float | None] = mapped_column(Float, index=True)
    group_id: Mapped[str | None] = mapped_column(String(64), index=True)
    city: Mapped[str | None] = mapped_column(String(128), index=True)
    region: Mapped[str | None] = mapped_column(String(128), index=True)
    revenue_segment: Mapped[str] = mapped_column(String(32), index=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_payer", "payer"),
        Index("ix_payments_beneficiary", "beneficiary"),
        Index("ix_payments_payer_beneficiary", "payer", "beneficiary"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    payer: Mapped[str] = mapped_column(String(32))
    beneficiary: Mapped[str] = mapped_column(String(32))
    amount: Mapped[float] = mapped_column(Float)
    count: Mapped[int] = mapped_column(Integer, default=0)


class PersonCompanyLink(Base):
    __tablename__ = "person_company_links"
    __table_args__ = (
        UniqueConstraint("synthetic_f", "synthetic_u"),
        Index("ix_person_company_links_company", "synthetic_u"),
        Index("ix_person_company_links_person", "synthetic_f"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    synthetic_f: Mapped[str] = mapped_column(String(32))
    synthetic_u: Mapped[str] = mapped_column(String(32))
    city_name: Mapped[str | None] = mapped_column(String(128))
    rc_name: Mapped[str | None] = mapped_column(String(128))


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped[BusinessProfile | None] = relationship(back_populates="user")


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    company_uid: Mapped[str | None] = mapped_column(
        ForeignKey("companies.uid", ondelete="SET NULL"), index=True
    )
    entrepreneur_name: Mapped[str] = mapped_column(String(128), default=DEFAULT_ENTREPRENEUR_NAME)
    business_name: Mapped[str] = mapped_column(String(255), default=DEFAULT_BUSINESS_NAME)
    role: Mapped[str | None] = mapped_column(String(32))
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    reporting_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    sources_initialized: Mapped[bool] = mapped_column(Boolean, default=False)
    search_history: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    notifications: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    onboarding_step: Mapped[str] = mapped_column(
        String(48), default=OnboardingStep.REGISTERED.value
    )
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile")
    company: Mapped[Company | None] = relationship()
    categories: Mapped[list[BusinessCategory]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    counterparties: Mapped[list[Counterparty]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    channel_subscriptions: Mapped[list[ProfileChannel]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    reporting_uploads: Mapped[list[ReportingUpload]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    @property
    def role_label(self) -> str | None:
        from back.core.constants import ROLE_LABELS

        try:
            return ROLE_LABELS[Role(self.role)] if self.role else None
        except ValueError:
            return None


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    handle: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    topics: Mapped[str] = mapped_column(String(255), default="")
    kind: Mapped[str] = mapped_column(String(16), default="catalog", index=True)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    subscriptions: Mapped[list[ProfileChannel]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class ProfileChannel(Base):
    __tablename__ = "profile_channels"
    __table_args__ = (UniqueConstraint("profile_id", "channel_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True
    )
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(16), default="catalog")
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    profile: Mapped[BusinessProfile] = relationship(back_populates="channel_subscriptions")
    channel: Mapped[Channel] = relationship(back_populates="subscriptions")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str] = mapped_column(String(128))
    group: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(Text)
    example: Mapped[str] = mapped_column(Text)
    channels: Mapped[list[str]] = mapped_column(JSONB, default=list)


class BusinessCategory(Base):
    __tablename__ = "business_categories"
    __table_args__ = (UniqueConstraint("profile_id", "category_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)

    profile: Mapped[BusinessProfile] = relationship(back_populates="categories")
    category: Mapped[Category] = relationship()


class Counterparty(Base):
    __tablename__ = "counterparties"
    __table_args__ = (
        UniqueConstraint("profile_id", "company_uid", "direction"),
        Index("ix_counterparties_profile_direction", "profile_id", "direction"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True
    )
    company_uid: Mapped[str | None] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(16), default=CounterpartyDirection.SUPPLIER.value)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    payments_count: Mapped[int] = mapped_column(Integer, default=0)
    share: Mapped[float] = mapped_column(Float, default=0.0)
    importance: Mapped[int] = mapped_column(Integer, default=0)
    default_name: Mapped[str] = mapped_column(String(128))
    custom_name: Mapped[str | None] = mapped_column(String(128))
    note: Mapped[str] = mapped_column(String(255), default="")

    profile: Mapped[BusinessProfile] = relationship(back_populates="counterparties")

    @property
    def display_name(self) -> str:
        return self.custom_name or self.default_name


class ReportingUpload(Base):
    __tablename__ = "reporting_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True
    )
    form_type: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(128))
    raw_text: Mapped[str] = mapped_column(Text, default="")
    extracted: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="processed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped[BusinessProfile] = relationship(back_populates="reporting_uploads")


class NewsEvent(Base):
    __tablename__ = "news_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(Text)
    what_it_means: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(String(512))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    importance: Mapped[int] = mapped_column(Integer, default=50, index=True)
    impact: Mapped[str] = mapped_column(String(16), default=Impact.NEUTRAL.value, index=True)
    category_ids: Mapped[list[int]] = mapped_column(JSONB, default=list)
    mentioned_company_uids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    facts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    source_posts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    impact_metrics: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    chain_key: Mapped[str | None] = mapped_column(String(64), index=True)
    update_label: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_feed_visible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrackedItem(Base):
    __tablename__ = "tracked_items"
    __table_args__ = (UniqueConstraint("profile_id", "event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("news_events.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), default="active")
    title: Mapped[str | None] = mapped_column(String(512))
    event_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    what_changed: Mapped[str | None] = mapped_column(Text)
    conclusions_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    event: Mapped[NewsEvent] = relationship()


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("profile_id", "event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("news_events.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventLike(Base):
    __tablename__ = "event_likes"
    __table_args__ = (UniqueConstraint("profile_id", "event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("news_events.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventQuestion(Base):
    __tablename__ = "event_questions"
    __table_args__ = (Index("ix_event_questions_profile_event", "profile_id", "event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_profiles.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("news_events.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="waiting")
    answer: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(128))
    date: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_cluster_key", "cluster_key"),
        Index("ix_posts_published_at", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(1024))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    parsed: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    categories: Mapped[list[int]] = mapped_column(JSONB, default=list)
    embedding: Mapped[list[float]] = mapped_column(JSONB, default=list)
    cluster_key: Mapped[str | None] = mapped_column(String(64))
    news_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("news_events.id", ondelete="SET NULL"), index=True
    )
    tracked_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tracked_items.id", ondelete="SET NULL")
    )
    importance: Mapped[int | None] = mapped_column(Integer)
    similarity: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    stage: Mapped[str] = mapped_column(String(32), default="received")
    decision_trace: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    news_event: Mapped[NewsEvent | None] = relationship()
