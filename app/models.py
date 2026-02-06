from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, Enum, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class PartnerType(enum.Enum):
    STRATEGIC = "strategic"
    CURRENT = "current"
    POTENTIAL = "potential"
    BLOCKED = "blocked"
    VIP = "vip"

class RiskLevel(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class ReportType(enum.Enum):
    WORD = "word"
    PDF = "pdf"
    EXCEL = "excel"

class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inn = Column(String(20), unique=True, nullable=False, index=True)
    legal_name = Column(String(255), nullable=False)
    trade_name = Column(String(255))
    partner_type = Column(Enum(PartnerType), default=PartnerType.CURRENT)
    category = Column(String(100))
    competitor = Column(String(255))

    email = Column(String(255))
    phone = Column(String(50))
    ceo_name = Column(String(255))
    cfo_name = Column(String(255))
    website = Column(String(255))

    addresses = Column(JSON)

    revenue_2023 = Column(Float(15, 2))
    revenue_2022 = Column(Float(15, 2))
    profit_2023 = Column(Float(15, 2))
    founding_year = Column(Integer)
    employee_count = Column(Integer)

    industry_code = Column(String(10))
    okved_code = Column(String(20))

    rating = Column(Float(3, 2))
    risk_level = Column(Enum(RiskLevel))
    payment_terms = Column(String(50))

    last_audit_date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_partner_type', 'partner_type'),
        Index('idx_category', 'category'),
        Index('idx_created_at', 'created_at'),
    )

class Turnover(Base):
    __tablename__ = "turnovers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    partner_inn = Column(String(20), ForeignKey('partners.inn', ondelete='CASCADE'), nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer)
    revenue = Column(Float(15, 2), nullable=False)
    profit = Column(Float(15, 2))
    transaction_count = Column(Integer)
    average_transaction = Column(Float(15, 2))

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_partner_year', 'partner_inn', 'year'),
    )

class BotInteraction(Base):
    __tablename__ = "bot_interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(Integer, nullable=False, index=True)
    telegram_username = Column(String(100))
    telegram_first_name = Column(String(100))
    telegram_last_name = Column(String(100))

    action_type = Column(String(50), nullable=False)
    partner_inn = Column(String(20))
    search_query = Column(Text)

    response_time_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        Index('idx_action_type', 'action_type'),
    )

class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_uuid = Column(String(36), unique=True, nullable=False, index=True)
    partner_inn = Column(String(20), ForeignKey('partners.inn', ondelete='CASCADE'), nullable=False)
    telegram_user_id = Column(Integer, nullable=False)

    report_type = Column(Enum(ReportType), default=ReportType.WORD)
    report_path = Column(String(500))
    file_size_bytes = Column(Integer)

    ai_analysis = Column(Text)
    generation_time_ms = Column(Integer)

    downloaded = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime)

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_user_partner', 'telegram_user_id', 'partner_inn'),
        Index('idx_created_at', 'created_at'),
    )
