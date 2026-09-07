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

INSERT INTO poc_term (term_code, description, aid_year_code, start_date, end_date)
VALUES ('202630', 'Summer 2026', '2526', DATE '2026-05-11', DATE '2026-08-07');

INSERT INTO poc_term (term_code, description, aid_year_code, start_date, end_date)
VALUES ('202640', 'Fall 2026', '2627', DATE '2026-08-24', DATE '2026-12-11');

-- Persons (synthetic identity)
INSERT INTO poc_person (banner_id, display_name, credit_limit)
VALUES ('D00010001', 'Demo Student One', 0);

INSERT INTO poc_person (banner_id, display_name, credit_limit, hold_ind)
VALUES ('D00010002', 'Demo Student Two (AR Hold)', 0, 'Y');

-- Transactions (TSADETL activity) - tuition charges + payments across four terms for student one
INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    1, 'TUIT', '202610', 1800, 1800, 1800, 'Y', 'A'
);

INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    2, 'CASH', '202610', 1800, -1800, -1800, 'N', 'A'
);

INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    3, 'TUIT', '202620', 2000, 2000, 2000, 'Y', 'A'
);

INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    4, 'CASH', '202620', 500, -500, -500, 'N', 'A'
);

INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    5, 'TUIT', '202630', 500, 500, 500, 'Y', 'A'
);

INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    6, 'CASH', '202630', 500, -500, -500, 'N', 'A'
);

INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    7, 'TUIT', '202640', 250, 250, 250, 'Y', 'A'
);

INSERT INTO poc_ar_transaction
    (person_key, transaction_no, detail_code, term_code, entry_amount,
     signed_amount, open_balance, original_charge_ind, status_code)
VALUES (
    (SELECT person_key FROM poc_person WHERE banner_id = 'D00010001'),
    8, 'CASH', '202640', 100, -100, -100, 'N', 'A'
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
    'TSADETL', 'DETAIL_CODE_DESCRIPTION', 'Detail Code Description column',
    'Detail Code Description is a separate field from Detail Code - it is a read-only, display-only column on this grid, not something you type into. It automatically shows whatever description text is stored for the Detail Code chosen on that row (e.g. selecting TUIT shows ''Tuition Charge''), looked up live from the detail code control table. Changing the Detail Code immediately changes this column too, since it is a mirrored lookup value, not independent data.',
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
    'TSADETL', 'NAME', 'Student name',
    'Name displays the name of the student loaded by the ID field. For the demo account D00010001, the displayed name is Demo Student One.'
);

INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text)
VALUES (
    'TSADETL', 'CREDIT_LIMIT', 'Credit limit',
    'Credit Limit displays the maximum credit amount configured for the loaded student. The demo account has a credit limit of 0.'
);

INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text)
VALUES (
    'TSADETL', 'HOLDS', 'Account holds',
    'Holds indicates whether an AR hold is active on the loaded account. It is blank when no hold is present and displays AR Hold when a hold is active.'
);

INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text)
VALUES (
    'TSADETL', 'START_OVER', 'Start Over action',
    'Start Over clears the currently loaded student, transactions, balance, and messages so another student ID can be entered.'
);

INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text)
VALUES (
    'TSADETL', 'GO', 'Go action',
    'Go loads the student account for the ID entered in the ID field, including the student''s name, credit limit, holds, transactions, and balance.'
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

INSERT INTO poc_help_metadata
    (page_code, field_name, topic, help_text)
VALUES (
    'TSADETL', 'DOWNLOAD_REPORT', 'Download Report',
    'The Student Account Detail Report is a formatted PDF for the student currently shown on the page. It includes a report number and date, the student''s name, ID, and account hold status, an itemized table of Charges/Payments (Term, Detail Code, Description, Amount, Balance for each transaction), and a summary section with the total of all entries and the current Account Balance. It is not a toolbar button on the page itself - it appears as a ''Download Report'' button, either after you drag-select over the student ID field, or after you ask the assistant (via a follow-up or typed question) for a report/download/export - and only once the account has at least one transaction. If the question names a specific term (e.g. "report for term 202610") and/or a specific detail code (e.g. "cash only"), the report and its balance are scoped to just that term and/or detail code instead of the whole account. This scoping happens only in how the report is generated from your question - the Charges/Payments grid on the page itself has no term or detail-code filter control.'
);
