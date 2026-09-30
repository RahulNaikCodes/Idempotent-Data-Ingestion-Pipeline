from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, model_validator

TOLERANCE = Decimal("0.01")
def _close(a: Decimal, b: Decimal) -> bool:
    """Return True if two money amounts match within the rounding tolerance."""
    return abs(a - b) <= TOLERANCE

class LineItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)        # must be strictly positive
    unit_price: Decimal = Field(ge=0)      # cannot be negative
    line_total: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def check_line_math(self) -> "LineItem":
        expected = self.quantity * self.unit_price
        if not _close(expected, self.line_total):
            raise ValueError(
                f"Line item '{self.description}': quantity ({self.quantity}) x "
                f"unit_price ({self.unit_price}) = {expected}, "
                f"but line_total is {self.line_total}"
            )
        return self

class ExtractedInvoice(BaseModel):

    vendor_name: str = Field(min_length=1)
    invoice_number: Optional[str] = None
    issue_date: date
    due_date: date
    currency: str = "USD"
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: Decimal = Field(ge=0)
    tax: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def check_invoice_invariants(self) -> "ExtractedInvoice":
        problems: list[str] = []
        # Invariant 1: the invoice can't be due before it was issued.
        if self.due_date < self.issue_date:
            problems.append(
                f"due_date ({self.due_date}) is earlier than issue_date ({self.issue_date})"
            )
        # Invariant 2: the line items must add up to the subtotal.
        items_sum = sum((item.line_total for item in self.line_items), Decimal("0"))
        if not _close(items_sum, self.subtotal):
            problems.append(
                f"Subtotal mismatch: line items sum to {items_sum}, "
                f"but subtotal is {self.subtotal}"
            )
        # Invariant 3: subtotal + tax must equal the grand total.
        expected_total = self.subtotal + self.tax
        if not _close(expected_total, self.total):
            problems.append(
                f"Total mismatch: subtotal ({self.subtotal}) + tax ({self.tax}) = "
                f"{expected_total}, but total is {self.total}"
            )
        if problems:
            raise ValueError("; ".join(problems))
        return self
