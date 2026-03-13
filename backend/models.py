from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    domain = Column(String, nullable=True)
    description = Column(String, nullable=True)
    founded_year = Column(Integer, nullable=True)
    yc_batch      = Column(String, nullable=True)  # e.g. "W24", "S23"
    funding_stage = Column(String, nullable=True)  # "Early" | "Growth" | "Public"
    # LinkedIn post metrics (fetched via Apify)
    linkedin_post_url   = Column(String,  nullable=True)
    linkedin_likes      = Column(Integer, nullable=True, default=0)
    linkedin_reposts    = Column(Integer, nullable=True, default=0)
    linkedin_fetched_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    funding_rounds = relationship(
        "FundingRound", back_populates="company", cascade="all, delete-orphan"
    )
    launch_posts = relationship(
        "LaunchPost", back_populates="company", cascade="all, delete-orphan"
    )
    contacts = relationship(
        "Contact", back_populates="company", cascade="all, delete-orphan"
    )


class FundingRound(Base):
    __tablename__ = "funding_rounds"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    amount     = Column(Float,  nullable=True)   # USD
    round_type = Column(String, nullable=True)   # pre-seed | seed | series_a …
    date       = Column(Date,   nullable=True)
    source     = Column(String, nullable=True)   # yc | crunchbase | manual …
    note       = Column(String, nullable=True)   # free-text annotation

    company = relationship("Company", back_populates="funding_rounds")


class LaunchPost(Base):
    __tablename__ = "launch_posts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    platform = Column(String, nullable=False)     # twitter | linkedin | hackernews
    post_url  = Column(String,  nullable=True)
    likes     = Column(Integer, nullable=True)
    reposts   = Column(Integer, nullable=True)
    date      = Column(Date,    nullable=True)
    has_video = Column(Boolean, nullable=False, default=False)

    company = relationship("Company", back_populates="launch_posts")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    x_handle = Column(String, nullable=True)

    company = relationship("Company", back_populates="contacts")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    twitter_likes_threshold = Column(Integer, default=200)
    linkedin_likes_threshold = Column(Integer, default=50)
