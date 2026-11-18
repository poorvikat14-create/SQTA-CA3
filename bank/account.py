"""System Under Test: a small banking-transactions module.

Business rules
--------------
* Deposit amount must be in [MIN_DEPOSIT, MAX_DEPOSIT].
* Withdrawals are capped at DAILY_WITHDRAW_LIMIT per day.
* SAVINGS accounts must keep at least MIN_SAVINGS_BALANCE after a withdrawal.
* CURRENT accounts may overdraw up to OVERDRAFT_LIMIT.
* Frozen accounts cannot send or receive money.
* Monthly interest (SAVINGS only) is tiered: <10,000 -> 3%, <100,000 -> 4%,
  otherwise 5% per annum, applied as rate / 12.
* A transfer is atomic: if the credit leg fails, the debit leg is rolled back.
"""

from decimal import Decimal, ROUND_HALF_UP

MIN_DEPOSIT = Decimal("1")
MAX_DEPOSIT = Decimal("100000")
DAILY_WITHDRAW_LIMIT = Decimal("20000")
MIN_SAVINGS_BALANCE = Decimal("500")
OVERDRAFT_LIMIT = Decimal("5000")

TIER1_CEILING = Decimal("10000")
TIER2_CEILING = Decimal("100000")
TIER1_RATE = Decimal("0.03")
TIER2_RATE = Decimal("0.04")
TIER3_RATE = Decimal("0.05")

SAVINGS = "SAVINGS"
CURRENT = "CURRENT"


class InvalidAmountError(ValueError):
    """Amount is out of range, non-positive, NaN or otherwise unusable."""


class InsufficientFundsError(Exception):
    """Withdrawal would break the balance / overdraft rule."""


class DailyLimitExceededError(Exception):
    """Withdrawal would push today's total above the daily limit."""


class AccountFrozenError(Exception):
    """Operation attempted on a frozen account."""


def _to_money(amount):
    """Validate and convert an amount to a 2-decimal Decimal."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float, str, Decimal)):
        raise TypeError("amount must be a number")
    try:
        value = Decimal(str(amount))
    except Exception:
        raise TypeError("amount must be a number")
    if not value.is_finite():
        raise InvalidAmountError("amount must be finite")
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Account:
    def __init__(self, owner, balance=0, account_type=SAVINGS):
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("owner must be a non-empty string")
        if account_type not in (SAVINGS, CURRENT):
            raise ValueError("account_type must be SAVINGS or CURRENT")
        opening = _to_money(balance)
        if opening < 0:
            raise InvalidAmountError("opening balance cannot be negative")
        self.owner = owner.strip()
        self.account_type = account_type
        self.balance = opening
        self.frozen = False
        self.withdrawn_today = Decimal("0.00")

    # ---- state ---------------------------------------------------------
    def freeze(self):
        self.frozen = True

    def unfreeze(self):
        self.frozen = False

    def reset_day(self):
        self.withdrawn_today = Decimal("0.00")

    def _check_active(self):
        if self.frozen:
            raise AccountFrozenError("account is frozen")

    # ---- operations ----------------------------------------------------
    def deposit(self, amount):
        self._check_active()
        value = _to_money(amount)
        if value < MIN_DEPOSIT or value > MAX_DEPOSIT:
            raise InvalidAmountError(
                f"deposit must be between {MIN_DEPOSIT} and {MAX_DEPOSIT}"
            )
        self.balance += value
        return self.balance

    def withdraw(self, amount):
        self._check_active()
        value = _to_money(amount)
        if value <= 0:
            raise InvalidAmountError("withdrawal must be positive")
        if self.withdrawn_today + value > DAILY_WITHDRAW_LIMIT:
            raise DailyLimitExceededError("daily withdrawal limit exceeded")
        if self.account_type == SAVINGS:
            if self.balance - value < MIN_SAVINGS_BALANCE:
                raise InsufficientFundsError("minimum savings balance would be breached")
        else:
            if self.balance - value < -OVERDRAFT_LIMIT:
                raise InsufficientFundsError("overdraft limit exceeded")
        self.balance -= value
        self.withdrawn_today += value
        return self.balance

    def transfer(self, target, amount):
        if target is self:
            raise ValueError("cannot transfer to the same account")
        value = _to_money(amount)
        self.withdraw(value)
        try:
            target.deposit(value)
        except Exception:
            # roll back the debit leg
            self.balance += value
            self.withdrawn_today -= value
            raise
        return self.balance

    def monthly_interest_rate(self):
        if self.balance < TIER1_CEILING:
            annual = TIER1_RATE
        elif self.balance < TIER2_CEILING:
            annual = TIER2_RATE
        else:
            annual = TIER3_RATE
        return annual

    def apply_monthly_interest(self):
        if self.account_type != SAVINGS:
            raise ValueError("interest applies to SAVINGS accounts only")
        self._check_active()
        interest = (self.balance * self.monthly_interest_rate() / 12).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        self.balance += interest
        return interest
