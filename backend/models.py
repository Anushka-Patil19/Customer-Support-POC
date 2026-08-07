from datetime import datetime, date

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from database import Base


class ArCategory(Base):
    """Simulates TTVDCAT -- detail category code validation."""

    __tablename__ = "poc_ar_category"

    category_code = Column(String(4), primary_key=True)
    description = Column(String(60), nullable=False)
    system_required_ind = Column(String(1), nullable=False, default="N")
    active_ind = Column(String(1), nullable=False, default="Y")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("system_required_ind IN ('Y','N')", name="ck_poc_ar_cat_sys"),
        CheckConstraint("active_ind IN ('Y','N')", name="ck_poc_ar_cat_active"),
    )

    def to_dict(self):
        return {
            "category_code": self.category_code,
            "description": self.description,
            "system_required_ind": self.system_required_ind,
            "active_ind": self.active_ind,
        }


class ArDetailCode(Base):
    """Simulates TSADETC -- student detail-code control."""

    __tablename__ = "poc_ar_detail_code"

    detail_code = Column(String(4), primary_key=True)
    description = Column(String(60), nullable=False)
    type_code = Column(String(1), nullable=False)  # C = charge, P = payment
    category_code = Column(String(4), ForeignKey("poc_ar_category.category_code"), nullable=False)
    grant_type_code = Column(String(4))
    priority_no = Column(Integer, nullable=False, default=0)
    term_based_ind = Column(String(1), nullable=False, default="Y")
    aid_year_based_ind = Column(String(1), nullable=False, default="N")
    refundable_ind = Column(String(1), nullable=False, default="N")
    receipt_ind = Column(String(1), nullable=False, default="N")
    active_ind = Column(String(1), nullable=False, default="Y")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("type_code IN ('C','P')", name="ck_poc_ar_det_type"),
        CheckConstraint("priority_no BETWEEN 0 AND 999", name="ck_poc_ar_det_priority"),
        CheckConstraint("term_based_ind IN ('Y','N')", name="ck_poc_ar_det_term_based"),
        CheckConstraint("aid_year_based_ind IN ('Y','N')", name="ck_poc_ar_det_aid_year"),
        CheckConstraint("refundable_ind IN ('Y','N')", name="ck_poc_ar_det_refundable"),
        CheckConstraint("receipt_ind IN ('Y','N')", name="ck_poc_ar_det_receipt"),
        CheckConstraint("active_ind IN ('Y','N')", name="ck_poc_ar_det_active"),
        CheckConstraint(
            "NOT (term_based_ind = 'Y' AND aid_year_based_ind = 'Y')",
            name="ck_poc_ar_det_period_type",
        ),
    )

    def to_dict(self):
        return {
            "detail_code": self.detail_code,
            "description": self.description,
            "type_code": self.type_code,
            "category_code": self.category_code,
            "grant_type_code": self.grant_type_code,
            "priority_no": self.priority_no,
            "term_based_ind": self.term_based_ind,
            "aid_year_based_ind": self.aid_year_based_ind,
            "refundable_ind": self.refundable_ind,
            "receipt_ind": self.receipt_ind,
            "active_ind": self.active_ind,
        }


class Person(Base):
    """Synthetic student/account identity (SPRIDEN-like)."""

    __tablename__ = "poc_person"

    person_key = Column(Integer, primary_key=True, autoincrement=True)
    banner_id = Column(String(9), nullable=False, unique=True)
    display_name = Column(String(120), nullable=False)
    active_ind = Column(String(1), nullable=False, default="Y")
    hold_ind = Column(String(1), nullable=False, default="N")
    credit_limit = Column(Numeric(12, 2))

    __table_args__ = (
        CheckConstraint("active_ind IN ('Y','N')", name="ck_poc_person_active"),
        CheckConstraint("hold_ind IN ('Y','N')", name="ck_poc_person_hold"),
    )

    def to_dict(self):
        return {
            "person_key": self.person_key,
            "banner_id": self.banner_id,
            "display_name": self.display_name,
            "active_ind": self.active_ind,
            "hold_ind": self.hold_ind,
            "credit_limit": float(self.credit_limit) if self.credit_limit is not None else None,
        }


class Term(Base):
    """Simulates STVTERM -- term validation."""

    __tablename__ = "poc_term"

    term_code = Column(String(6), primary_key=True)
    description = Column(String(60), nullable=False)
    aid_year_code = Column(String(4))
    start_date = Column(Date)
    end_date = Column(Date)
    active_ind = Column(String(1), nullable=False, default="Y")

    __table_args__ = (CheckConstraint("active_ind IN ('Y','N')", name="ck_poc_term_active"),)

    def to_dict(self):
        return {
            "term_code": self.term_code,
            "description": self.description,
            "aid_year_code": self.aid_year_code,
            "start_date": self.start_date.isoformat() if isinstance(self.start_date, date) else self.start_date,
            "end_date": self.end_date.isoformat() if isinstance(self.end_date, date) else self.end_date,
            "active_ind": self.active_ind,
        }


class ArTransaction(Base):
    """Simulates TSADETL account-detail activity (TBRACCD-like)."""

    __tablename__ = "poc_ar_transaction"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    person_key = Column(Integer, ForeignKey("poc_person.person_key"), nullable=False)
    transaction_no = Column(Integer, nullable=False)
    detail_code = Column(String(4), ForeignKey("poc_ar_detail_code.detail_code"), nullable=False)
    term_code = Column(String(6), ForeignKey("poc_term.term_code"), nullable=False)
    aid_year_code = Column(String(4))
    entry_amount = Column(Numeric(12, 2), nullable=False)
    signed_amount = Column(Numeric(12, 2), nullable=False)
    open_balance = Column(Numeric(12, 2), nullable=False)
    original_charge_ind = Column(String(1), nullable=False, default="N")
    status_code = Column(String(1), nullable=False, default="A")  # A = active, V = voided
    transaction_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("person_key", "transaction_no", name="uk_poc_ar_tran_no"),
        CheckConstraint("entry_amount > 0", name="ck_poc_ar_tran_entry_amt"),
        CheckConstraint("original_charge_ind IN ('Y','N')", name="ck_poc_ar_tran_original"),
        CheckConstraint("status_code IN ('A','V')", name="ck_poc_ar_tran_status"),
    )

    def to_dict(self):
        return {
            "transaction_id": self.transaction_id,
            "person_key": self.person_key,
            "transaction_no": self.transaction_no,
            "detail_code": self.detail_code,
            "term_code": self.term_code,
            "aid_year_code": self.aid_year_code,
            "entry_amount": float(self.entry_amount),
            "signed_amount": float(self.signed_amount),
            "open_balance": float(self.open_balance),
            "original_charge_ind": self.original_charge_ind,
            "status_code": self.status_code,
            "transaction_date": self.transaction_date.isoformat()
            if isinstance(self.transaction_date, date)
            else self.transaction_date,
        }


class ArAccountSummary(Base):
    """Optional cached/demo balance region on TSADETL."""

    __tablename__ = "poc_ar_account_summary"

    person_key = Column(Integer, ForeignKey("poc_person.person_key"), primary_key=True)
    term_code = Column(String(6), ForeignKey("poc_term.term_code"), primary_key=True)
    account_balance = Column(Numeric(12, 2), nullable=False, default=0)
    refreshed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class HelpMetadata(Base):
    """RAG/help facts and page-field lineage used by the Deep Dive assistant."""

    __tablename__ = "poc_help_metadata"

    help_id = Column(Integer, primary_key=True, autoincrement=True)
    page_code = Column(String(8), nullable=False)
    field_name = Column(String(60))
    topic = Column(String(100), nullable=False)
    help_text = Column(Text, nullable=False)
    source_page_code = Column(String(8))
    source_object_name = Column(String(30))
    target_page_code = Column(String(8))
    target_object_name = Column(String(30))
    active_ind = Column(String(1), nullable=False, default="Y")

    __table_args__ = (CheckConstraint("active_ind IN ('Y','N')", name="ck_poc_help_active"),)
