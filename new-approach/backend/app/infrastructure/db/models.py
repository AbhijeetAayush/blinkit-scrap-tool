from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("workspace_id", "query"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("workspace_id", "platform", "lat", "lon"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(Text, default="blinkit")
    pincode: Mapped[str] = mapped_column(Text, nullable=False)
    store_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    pages_ok: Mapped[int] = mapped_column(Integer, default=0)
    pages_fail: Mapped[int] = mapped_column(Integer, default=0)
    jobs_total: Mapped[int] = mapped_column(Integer, default=0)
    jobs_done: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    jobs: Mapped[list[RunJob]] = relationship("RunJob", back_populates="run")


class RunJob(Base):
    __tablename__ = "run_jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"))
    queries: Mapped[list] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run: Mapped[Run] = relationship("Run", back_populates="jobs")


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("platform", "merchant_id", "pincode", "product_id", "search_query", "run_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_id: Mapped[str] = mapped_column(Text, nullable=False)
    pincode: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[str] = mapped_column(Text, nullable=False)
    variant_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_query: Mapped[str] = mapped_column(Text, default="")
    sku_name: Mapped[str] = mapped_column(Text, nullable=False)
    brand_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    pack_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    pack_ml: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pack_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mrp: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    selling_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    discount_percent: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    discount_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    offer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(Text, default="INR")
    availability: Mapped[str] = mapped_column(Text, default="in_stock")
    inventory_shown: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qty_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    low_stock_badge: Mapped[bool] = mapped_column(Boolean, default=False)
    shelf_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    organic_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_sponsored: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rating_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_promise_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_time_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_price_per_kg: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    unit_price_per_l: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    category_path: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    result_page: Mapped[int | None] = mapped_column(Integer, default=1)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
