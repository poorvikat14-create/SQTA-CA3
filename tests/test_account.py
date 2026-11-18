"""pytest suite for bank.account.

Author split: tests tagged "B" were designed by Student B (test design / SUT),
the tool wiring (fixtures, parametrization, markers, mocks) is Student A.
Test IDs (TC-xx) match the test matrix in the slides.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest

from bank import (
    Account,
    AccountFrozenError,
    DailyLimitExceededError,
    InsufficientFundsError,
    InvalidAmountError,
)

D = Decimal


# ---------------------------------------------------------------- creation
class TestCreation:
    def test_tc01_valid_account(self):
        a = Account("  Asha ", 100)
        assert a.owner == "Asha" and a.balance == D("100.00")
        assert a.account_type == "SAVINGS" and not a.frozen

    @pytest.mark.parametrize("owner", ["", "   ", None, 42])
    def test_tc02_bad_owner(self, owner):
        with pytest.raises(ValueError):
            Account(owner)

    def test_tc03_bad_type(self):
        with pytest.raises(ValueError):
            Account("A", 0, "FIXED")

    def test_tc04_negative_opening_balance(self):
        with pytest.raises(InvalidAmountError):
            Account("A", -1)


# ----------------------------------------------------------------- deposit
class TestDepositBoundary:
    """BVA on deposit range [1, 100000]."""

    @pytest.mark.parametrize(
        "amount, ok",
        [
            (0, False),          # TC-05 min-1
            (1, True),           # TC-06 min
            (2, True),           # TC-07 min+1
            (50000, True),       # TC-08 nominal
            (99999, True),       # TC-09 max-1
            (100000, True),      # TC-10 max
            (100001, False),     # TC-11 max+1
        ],
    )
    def test_deposit_boundaries(self, savings, amount, ok):
        before = savings.balance
        if ok:
            assert savings.deposit(amount) == before + D(amount)
        else:
            with pytest.raises(InvalidAmountError):
                savings.deposit(amount)
            assert savings.balance == before

    @pytest.mark.parametrize("amount", [-5, -0.01, 0.0])
    def test_tc12_non_positive(self, savings, amount):
        with pytest.raises(InvalidAmountError):
            savings.deposit(amount)

    @pytest.mark.parametrize("amount", ["abc", None, [1], True, object()])
    def test_tc13_type_errors(self, savings, amount):
        with pytest.raises(TypeError):
            savings.deposit(amount)

    @pytest.mark.parametrize("amount", [float("nan"), float("inf")])
    def test_tc14_nan_inf(self, savings, amount):
        with pytest.raises(InvalidAmountError):
            savings.deposit(amount)

    def test_tc15_string_numeric_and_rounding(self, savings):
        savings.deposit("100.005")   # half-up -> 100.01
        assert savings.balance == D("10100.01")

    def test_tc16_frozen_cannot_deposit(self, savings):
        savings.freeze()
        with pytest.raises(AccountFrozenError):
            savings.deposit(10)
        savings.unfreeze()
        savings.deposit(10)


# ---------------------------------------------------------------- withdraw
class TestWithdraw:
    def test_tc17_normal(self, savings):
        assert savings.withdraw(1000) == D("9000.00")
        assert savings.withdrawn_today == D("1000.00")

    @pytest.mark.parametrize("amount", [0, -1])
    def test_tc18_non_positive(self, savings, amount):
        with pytest.raises(InvalidAmountError):
            savings.withdraw(amount)

    @pytest.mark.parametrize(
        "amount, ok",
        [(9499, True), (9500, True), (9501, False)],   # TC-19..21 min balance 500
    )
    def test_savings_min_balance_boundary(self, savings, amount, ok):
        if ok:
            savings.withdraw(amount)
            assert savings.balance >= D("500")
        else:
            with pytest.raises(InsufficientFundsError):
                savings.withdraw(amount)
            assert savings.balance == D("10000.00")

    @pytest.mark.parametrize(
        "amount, ok",
        [(5999, True), (6000, True), (6001, False)],   # TC-22..24 overdraft -5000
    )
    def test_current_overdraft_boundary(self, current, amount, ok):
        if ok:
            current.withdraw(amount)
            assert current.balance >= D("-5000")
        else:
            with pytest.raises(InsufficientFundsError):
                current.withdraw(amount)

    def test_tc25_daily_limit_boundary(self):
        a = Account("Rich", 90000, "SAVINGS")
        a.withdraw(19999)
        a.withdraw(1)                       # exactly 20000 total
        with pytest.raises(DailyLimitExceededError):
            a.withdraw(1)

    def test_tc26_single_withdraw_over_limit(self):
        a = Account("Rich", 90000, "SAVINGS")
        with pytest.raises(DailyLimitExceededError):
            a.withdraw(20001)

    def test_tc27_reset_day(self):
        a = Account("Rich", 90000, "SAVINGS")
        a.withdraw(20000)
        a.reset_day()
        a.withdraw(20000)
        assert a.balance == D("50000.00")

    def test_tc28_frozen_cannot_withdraw(self, savings):
        savings.freeze()
        with pytest.raises(AccountFrozenError):
            savings.withdraw(10)

    def test_tc29_failed_withdraw_leaves_state(self, savings):
        with pytest.raises(InsufficientFundsError):
            savings.withdraw(9600)
        assert savings.balance == D("10000.00")
        assert savings.withdrawn_today == D("0.00")


# ---------------------------------------------------------------- transfer
class TestTransfer:
    def test_tc30_success(self, savings, other):
        savings.transfer(other, 1500)
        assert savings.balance == D("8500.00")
        assert other.balance == D("3500.00")

    def test_tc31_self_transfer(self, savings):
        with pytest.raises(ValueError):
            savings.transfer(savings, 10)

    def test_tc32_insufficient_funds_no_credit(self, savings, other):
        with pytest.raises(InsufficientFundsError):
            savings.transfer(other, 9600)
        assert other.balance == D("2000.00")

    def test_tc33_rollback_when_target_frozen(self, savings, other):
        other.freeze()
        with pytest.raises(AccountFrozenError):
            savings.transfer(other, 1000)
        assert savings.balance == D("10000.00")        # debit rolled back
        assert savings.withdrawn_today == D("0.00")
        assert other.balance == D("2000.00")

    def test_tc34_rollback_with_mock_target(self, savings):
        """Mock setup: target.deposit explodes -> sender must be restored."""
        class Boom(Exception):
            pass

        target = Account("T", 0)
        with patch.object(Account, "deposit", side_effect=Boom):
            with pytest.raises(Boom):
                savings.transfer(target, 700)
        assert savings.balance == D("10000.00")

    def test_tc35_frozen_sender(self, savings, other):
        savings.freeze()
        with pytest.raises(AccountFrozenError):
            savings.transfer(other, 10)

    def test_tc36_transfer_bad_amount(self, savings, other):
        with pytest.raises(InvalidAmountError):
            savings.transfer(other, 0)


# ---------------------------------------------------------------- interest
class TestInterest:
    @pytest.mark.parametrize(
        "balance, expected_interest",
        [
            (500, "1.25"),            # tier 1: 500*0.03/12
            (9999.99, "25.00"),       # TC-37 just below 10,000
            (10000, "33.33"),         # TC-38 boundary -> tier 2
            (99999.99, "333.33"),     # TC-39 just below 100,000
            (100000, "416.67"),       # TC-40 boundary -> tier 3
            (240000, "1000.00"),
        ],
    )
    def test_tiers(self, balance, expected_interest):
        a = Account("I", balance, "SAVINGS")
        assert a.apply_monthly_interest() == D(expected_interest)

    def test_tc41_balance_updated(self):
        a = Account("I", 12000, "SAVINGS")
        i = a.apply_monthly_interest()
        assert a.balance == D("12000.00") + i

    def test_tc42_current_not_eligible(self, current):
        with pytest.raises(ValueError):
            current.apply_monthly_interest()

    def test_tc43_frozen_no_interest(self, savings):
        savings.freeze()
        with pytest.raises(AccountFrozenError):
            savings.apply_monthly_interest()

    def test_tc44_rate_helper(self):
        assert Account("x", 0).monthly_interest_rate() == D("0.03")
        assert Account("x", 50000).monthly_interest_rate() == D("0.04")
        assert Account("x", 500000).monthly_interest_rate() == D("0.05")
