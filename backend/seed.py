"""Idempotent seed loader -- ports the same rows as sql/02_seed_data.sql into
the runtime SQLite DB, plus a few extra help_metadata rows so the Deep Dive
assistant has static grounding for TTVDCAT and TSADETC (the original seed
file only wrote help rows for TSADETL). Every added fact restates something
already stated in the technical design doc (secs 3.1, 3.2, 7.1, 7.2) -- none
of it is invented.
"""
from datetime import date

from database import SessionLocal
from models import ArCategory, ArDetailCode, ArTransaction, HelpMetadata, Person, Term


def run():
    db = SessionLocal()
    try:
        if db.query(ArCategory).count() > 0:
            return

        db.add_all(
            [
                ArCategory(category_code="FA", description="Financial Aid", system_required_ind="N"),
                ArCategory(category_code="FEE", description="Registration Fees", system_required_ind="Y"),
                ArCategory(category_code="CSH", description="Cash", system_required_ind="N"),
            ]
        )

        db.add_all(
            [
                ArDetailCode(
                    detail_code="TUIT", description="Tuition Charge", type_code="C", category_code="FEE",
                    priority_no=100, term_based_ind="Y", aid_year_based_ind="N",
                    refundable_ind="N", receipt_ind="N", active_ind="Y",
                ),
                ArDetailCode(
                    detail_code="PELL", description="Federal Pell Grant", type_code="P", category_code="FA",
                    priority_no=10, term_based_ind="N", aid_year_based_ind="Y",
                    refundable_ind="Y", receipt_ind="N", active_ind="Y",
                ),
                ArDetailCode(
                    detail_code="CASH", description="Cash Payment", type_code="P", category_code="CSH",
                    priority_no=20, term_based_ind="Y", aid_year_based_ind="N",
                    refundable_ind="Y", receipt_ind="Y", active_ind="Y",
                ),
                ArDetailCode(
                    detail_code="GFLX", description="Grad Flex Fee", type_code="C", category_code="FEE",
                    priority_no=150, term_based_ind="Y", aid_year_based_ind="N",
                    refundable_ind="N", receipt_ind="N", active_ind="N",
                ),
            ]
        )

        db.add_all(
            [
                Term(
                    term_code="202620", description="Spring 2026", aid_year_code="2526",
                    start_date=date(2026, 1, 12), end_date=date(2026, 5, 8),
                ),
                Term(
                    term_code="202610", description="Fall 2025", aid_year_code="2526",
                    start_date=date(2025, 8, 25), end_date=date(2025, 12, 12),
                ),
            ]
        )

        db.add_all(
            [
                Person(banner_id="D00010001", display_name="Demo Student One", credit_limit=0, hold_ind="N"),
                Person(
                    banner_id="D00010002", display_name="Demo Student Two (AR Hold)",
                    credit_limit=0, hold_ind="Y",
                ),
            ]
        )
        db.flush()  # populate person_key for the transactions below

        student_one = db.query(Person).filter_by(banner_id="D00010001").one()
        db.add_all(
            [
                ArTransaction(
                    person_key=student_one.person_key, transaction_no=1, detail_code="TUIT",
                    term_code="202620", entry_amount=2000, signed_amount=2000, open_balance=2000,
                    original_charge_ind="Y", status_code="A",
                ),
                ArTransaction(
                    person_key=student_one.person_key, transaction_no=2, detail_code="CASH",
                    term_code="202620", entry_amount=500, signed_amount=500, open_balance=500,
                    original_charge_ind="N", status_code="A",
                ),
            ]
        )

        db.add_all(
            [
                HelpMetadata(
                    page_code="TSADETL", field_name="DETAIL_CODE", topic="Detail code meaning",
                    help_text=(
                        "The Detail Code identifies the specific charge or payment type applied to a "
                        "student account. It must exist and be active in the detail code control table "
                        "before it can be used here."
                    ),
                    source_page_code="TSADETC", source_object_name="POC_AR_DETAIL_CODE",
                ),
                HelpMetadata(
                    page_code="TSADETL", field_name="CATEGORY", topic="Category provenance",
                    help_text=(
                        "The Category groups detail codes for reporting and validation (e.g. Financial "
                        "Aid, Fees, Cash). It is created and maintained on the category validation screen, "
                        "not on this page."
                    ),
                    source_page_code="TTVDCAT", source_object_name="POC_AR_CATEGORY",
                ),
                HelpMetadata(
                    page_code="TSADETL", field_name="BALANCE", topic="Balance calculation",
                    help_text=(
                        "Balance is the sum of open_balance across all active (non-voided) transactions "
                        "for the student. Charges add to the balance; payments subtract from it."
                    ),
                ),
                HelpMetadata(
                    page_code="TSADETL", field_name="TYPE_CODE", topic="Charge vs payment",
                    help_text=(
                        "Type C (Charge) increases the account balance; Type P (Payment) decreases it. "
                        "The sign is applied automatically based on the detail code's type -- it is not "
                        "user-entered."
                    ),
                ),
                HelpMetadata(
                    page_code="TTVDCAT", field_name="CODE", topic="Category code rules",
                    help_text=(
                        "The Code is the short category identifier used on this validation page. It must "
                        "be uppercase, 1-4 characters, contain no spaces, and be unique -- once saved it "
                        "is the key other screens use to reference this category."
                    ),
                ),
                HelpMetadata(
                    page_code="TTVDCAT", field_name="SYSTEM_REQUIRED", topic="System required categories",
                    help_text=(
                        "System Required marks categories that were delivered as baseline data. Users "
                        "cannot delete a system-required category; colleges can still create and delete "
                        "their own non-system-required categories freely."
                    ),
                ),
                HelpMetadata(
                    page_code="TTVDCAT", field_name=None, topic="Category usage",
                    help_text=(
                        "A category groups related detail codes for reporting and validation. To see "
                        "every detail code assigned to a category, ask where that category is used -- it "
                        "is looked up live from the detail-code table."
                    ),
                    target_page_code="TSADETC", target_object_name="POC_AR_DETAIL_CODE",
                ),
                HelpMetadata(
                    page_code="TSADETC", field_name="CATEGORY", topic="Category foreign key",
                    help_text=(
                        "Category must be a valid, active code maintained on the TTVDCAT validation page. "
                        "This page does not let you create a new category inline -- if the category you "
                        "need does not exist yet, it must be added on TTVDCAT first."
                    ),
                    source_page_code="TTVDCAT", source_object_name="POC_AR_CATEGORY",
                ),
                HelpMetadata(
                    page_code="TSADETC", field_name="PRIORITY", topic="Priority ordering",
                    help_text=(
                        "Priority is a three-digit number (000-999) used to order how detail codes are "
                        "applied or listed relative to each other; it does not affect whether a detail "
                        "code is valid or active."
                    ),
                ),
                HelpMetadata(
                    page_code="TSADETC", field_name="ACTIVE", topic="Active indicator",
                    help_text=(
                        "A detail code must have its Active indicator set to Y before it can be used for "
                        "new transactions on TSADETL. Deactivating a code (setting Active to N) hides it "
                        "from new entry but existing transaction history that already used it remains "
                        "visible."
                    ),
                ),
            ]
        )

        db.commit()
    finally:
        db.close()
