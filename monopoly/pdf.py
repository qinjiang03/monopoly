import dataclasses
import os
import re
from datetime import datetime

import pytesseract
from fitz import Document, csGRAY
from google.cloud import storage
from pandas import DataFrame
from PIL import Image

from monopoly.config import settings
from monopoly.constants import AMOUNT, DATE, DESCRIPTION, ROOT_DIR
from monopoly.helpers import generate_name, upload_to_google_cloud_storage


@dataclasses.dataclass
class Statement:
    bank: str
    account_name: str
    date: datetime
    date_pattern: str
    transaction_pattern: str
    filename: str = "statement.csv"


class PDF:
    def __init__(self, file_path: str = "", password: str = ""):
        self.file_path: str = file_path
        self.password: str = password
        self.file_name: str
        self.pages: list[list[str]]
        self.df: DataFrame

        self.statement: Statement

    def _open_pdf(self):
        pdf = Document(self.file_path)
        pdf.authenticate(password=self.password)

        if pdf.is_encrypted:
            raise ValueError("Wrong password - document is encrypted")

        self.file_name = pdf.name

        return pdf

    def _extract_text_from_pdf(self) -> list[list[str]]:
        doc = self._open_pdf()
        pages = []

        for _, page_data in enumerate(doc):
            pix = page_data.get_pixmap(dpi=300, colorspace=csGRAY)
            image = Image.frombytes("L", [pix.width, pix.height], pix.samples)

            text = pytesseract.image_to_string(image)
            lines = text.split("\n")
            pages.append(lines)

        return pages

    def _extract_transactions_from_text(self, pages) -> list[dict[str, str]]:
        transactions = []
        for page in pages:
            for line in page:
                match = re.match(self.statement.transaction_pattern, line)
                if match:
                    date, description, amount = match.groups()

                    transactions.append(
                        {DATE: date, DESCRIPTION: description, AMOUNT: amount}
                    )

            return transactions

    def extract_df_from_pdf(self, columns: list = None) -> DataFrame:
        if not columns:
            columns = [DATE, DESCRIPTION, AMOUNT]
        self.pages = self._extract_text_from_pdf()
        transactions = self._extract_transactions_from_text(self.pages)

        return DataFrame(transactions, columns=columns)

    @staticmethod
    def transform_amount_to_float(df: DataFrame):
        df[AMOUNT] = df[AMOUNT].astype(float)
        return df

    def _write_to_csv(self, df: DataFrame):
        self.statement.filename = generate_name("file", self.statement)

        file_path = os.path.join(ROOT_DIR, "output", self.statement.filename)
        df.to_csv(file_path, index=False)

        return file_path

    def load(self, df: DataFrame, upload_to_cloud: bool = False):
        csv_file_path = self._write_to_csv(df)

        if upload_to_cloud:
            blob_name = generate_name("blob", self.statement)
            upload_to_google_cloud_storage(
                client=storage.Client(),
                source_filename=csv_file_path,
                bucket_name=settings.gcs_bucket,
                blob_name=blob_name,
            )
