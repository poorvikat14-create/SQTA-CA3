import pytest

from bank import Account


@pytest.fixture
def savings():
    return Account("Asha", 10000, "SAVINGS")


@pytest.fixture
def current():
    return Account("Ravi", 1000, "CURRENT")


@pytest.fixture
def other():
    return Account("Meera", 2000, "SAVINGS")
