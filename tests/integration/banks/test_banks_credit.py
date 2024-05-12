from datetime import datetime
from pathlib import Path

import pytest
from test_utils.skip import skip_if_encrypted
from test_utils.transactions import get_transactions_as_dict, read_transactions_from_csv

from monopoly.banks import Citibank, Dbs, Hsbc, Ocbc, StandardChartered
from monopoly.banks.base import BankBase
from monopoly.pipeline import Pipeline
from monopoly.statements import CreditStatement

test_cases = [
    (Citibank, -1414.07, datetime(2022, 11, 15)),
    (Dbs, -16969.17, datetime(2023, 10, 15)),
    (Hsbc, -1218.2, datetime(2023, 8, 20)),
    (Ocbc, -702.1, datetime(2023, 8, 1)),
    (StandardChartered, -82.45, datetime(2023, 5, 16)),
]


@skip_if_encrypted
@pytest.mark.parametrize(
    "bank, total_amount, statement_date",
    test_cases,
)
def test_bank_credit_statements(
    bank: BankBase,
    total_amount: float,
    statement_date: datetime,
):
    bank_name = bank.credit_config.bank_name
    test_directory = Path(__file__).parent / bank_name / "credit"
    pipeline = Pipeline(test_directory / "input.pdf")
    statement: CreditStatement = pipeline.extract()

    # check raw data
    expected_raw_transactions = read_transactions_from_csv(test_directory, "raw.csv")
    raw_transactions_as_dict = get_transactions_as_dict(statement.transactions)
    expected_transaction_total_amount = [
        transaction.amount for transaction in statement.transactions
    ]
    assert expected_raw_transactions == raw_transactions_as_dict
    assert round(sum(expected_transaction_total_amount), 2) == total_amount
    assert statement.statement_date == statement_date

    # check transformed data
    expected_transformed_transactions = read_transactions_from_csv(
        test_directory, "transformed.csv"
    )
    transformed_transactions = pipeline.transform(
        transactions=statement.transactions,
        statement_date=statement.statement_date,
        transaction_date_order=statement.config.transaction_date_order,
    )
    transformed_transactions_as_dict = get_transactions_as_dict(
        transformed_transactions
    )
    assert expected_transformed_transactions == transformed_transactions_as_dict
