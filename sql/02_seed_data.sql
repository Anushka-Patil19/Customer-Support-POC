--------------------------------------------------------------------------------
-- Banner AR Interactive Help POC - Seed Data
-- Run after 01_schema.sql
--------------------------------------------------------------------------------

-- Categories (TTVDCAT)
INSERT INTO poc_ar_category (category_code, description, system_required_ind)
VALUES ('FA', 'Financial Aid', 'N');

INSERT INTO poc_ar_category (category_code, description, system_required_ind)
VALUES ('FEE', 'Registration Fees', 'Y');

INSERT INTO poc_ar_category (category_code, description, system_required_ind)
VALUES ('CSH', 'Cash', 'N');

-- Detail codes (TSADETC)
INSERT INTO poc_ar_detail_code
    (detail_code, description, type_code, category_code, priority_no,
     term_based_ind, aid_year_based_ind, refundable_ind, receipt_ind, active_ind)
VALUES
    ('TUIT', 'Tuition Charge', 'C', 'FEE', 100, 'Y', 'N', 'N', 'N', 'Y');

INSERT INTO poc_ar_detail_code
    (detail_code, description, type_code, category_code, priority_no,
     term_based_ind, aid_year_based_ind, refundable_ind, receipt_ind, active_ind)
VALUES
    ('PELL', 'Federal Pell Grant', 'P', 'FA', 10, 'N', 'Y', 'Y', 'N', 'Y');

INSERT INTO poc_ar_detail_code
    (detail_code, description, type_code, category_code, priority_no,
     term_based_ind, aid_year_based_ind, refundable_ind, receipt_ind, active_ind)
VALUES
    ('CASH', 'Cash Payment', 'P', 'CSH', 20, 'Y', 'N', 'Y', 'Y', 'Y');

-- An inactive detail code, to exercise the "why don't I see this code" help scenario
INSERT INTO poc_ar_detail_code
    (detail_code, description, type_code, category_code, priority_no,
     term_based_ind, aid_year_based_ind, refundable_ind, receipt_ind, active_ind)
VALUES
    ('GFLX', 'Grad Flex Fee', 'C', 'FEE', 150, 'Y', 'N', 'N', 'N', 'N');

-- Terms (STVTERM)
INSERT INTO poc_term (term_code, description, aid_year_code, start_date, end_date)
VALUES ('202620', 'Spring 2026', '2526', DATE '2026-01-12', DATE '2026-05-08');

INSERT INTO poc_term (term_code, description, aid_year_code, start_date, end_date)
VALUES ('202610', 'Fall 2025', '2526', DATE '2025-08-25', DATE '2025-12-12');

-- Persons (synthetic identity)
INSERT INTO poc_person (banner_id, display_name, credit_limit)
VALUES ('D00010001', 'Demo Student One', 0);

INSERT INTO poc_person (banner_id, display_name, credit_limit, hold_ind)
VALUES ('D00010002', 'Demo Student Two (AR Hold)', 0, 'Y');

-- Transactions (TSADETL activity) - tuition charge + partial payment for student one
INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    1, 'TUIT', '202620', 2000, 2000, 2000, 'Y', 'A'
);

INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    2, 'CASH', '202620', 500, 500, 500, 'N', 'A'
);

-- Help metadata (RAG facts / lineage) referenced by the TSADETL deep-dive
INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text, source_page_code, source_object_name)
VALUES (
    'TSADETL', 'DETAIL_CODE', 'Detail code meaning',
    'The Detail Code identifies the specific charge or payment type applied to a student account. It must exist and be active in the detail code control table before it can be used here.',
    'TSADETC', 'POC_AR_DETAIL_CODE'
);

INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text, source_page_code, source_object_name)
VALUES (
    'TSADETL', 'CATEGORY', 'Category provenance',
    'The Category groups detail codes for reporting and validation (e.g. Financial Aid, Fees, Cash). It is created and maintained on the category validation screen, not on this page.',
    'TTVDCAT', 'POC_AR_CATEGORY'
);

INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text)
VALUES (
    'TSADETL', 'BALANCE', 'Balance calculation',
    'Balance is the sum of open_balance across all active (non-voided) transactions for the student. Charges add to the balance; payments subtract from it.'
);

INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text)
VALUES (
    'TSADETL', 'TYPE_CODE', 'Charge vs payment',
    'Type C (Charge) increases the account balance; Type P (Payment) decreases it. The sign is applied automatically based on the detail code''s type - it is not user-entered.'
);
