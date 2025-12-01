"""Tests for the querychat.data module."""

import pandas as pd
from querychat.data import tips, titanic


def test_titanic_returns_dataframe():
    """Test that titanic() returns a pandas DataFrame."""
    df = titanic()
    assert isinstance(df, pd.DataFrame)


def test_titanic_has_expected_shape():
    """Test that the Titanic dataset has the expected number of rows and columns."""
    df = titanic()
    assert df.shape == (891, 15), f"Expected (891, 15) but got {df.shape}"


def test_titanic_has_expected_columns():
    """Test that the Titanic dataset has the expected column names."""
    df = titanic()
    expected_columns = [
        "survived",
        "pclass",
        "sex",
        "age",
        "sibsp",
        "parch",
        "fare",
        "embarked",
        "class",
        "who",
        "adult_male",
        "deck",
        "embark_town",
        "alive",
        "alone",
    ]
    assert list(df.columns) == expected_columns


def test_titanic_data_integrity():
    """Test basic data integrity of the Titanic dataset."""
    df = titanic()

    # Check that survived column has only 0 and 1 values
    assert set(df["survived"].dropna().unique()) <= {0, 1}

    # Check that pclass has only 1, 2, 3
    assert set(df["pclass"].dropna().unique()) <= {1, 2, 3}

    # Check that sex has only 'male' and 'female'
    assert set(df["sex"].dropna().unique()) <= {"male", "female"}

    # Check that fare is non-negative
    assert (df["fare"].dropna() >= 0).all()


def test_titanic_creates_new_copy():
    """Test that titanic() returns a new copy each time it's called."""
    df1 = titanic()
    df2 = titanic()

    # They should not be the same object
    assert df1 is not df2

    # But they should have the same data
    assert df1.equals(df2)


def test_tips_returns_dataframe():
    """Test that tips() returns a pandas DataFrame."""
    df = tips()
    assert isinstance(df, pd.DataFrame)


def test_tips_has_expected_shape():
    """Test that the tips dataset has the expected number of rows and columns."""
    df = tips()
    assert df.shape == (244, 7), f"Expected (244, 7) but got {df.shape}"


def test_tips_has_expected_columns():
    """Test that the tips dataset has the expected column names."""
    df = tips()
    expected_columns = [
        "total_bill",
        "tip",
        "sex",
        "smoker",
        "day",
        "time",
        "size",
    ]
    assert list(df.columns) == expected_columns


def test_tips_data_integrity():
    """Test basic data integrity of the tips dataset."""
    df = tips()

    # Check that total_bill is positive
    assert (df["total_bill"] > 0).all()

    # Check that tip is non-negative
    assert (df["tip"] >= 0).all()

    # Check that sex has only expected values
    assert set(df["sex"].dropna().unique()) <= {"Male", "Female"}

    # Check that smoker has only expected values
    assert set(df["smoker"].dropna().unique()) <= {"Yes", "No"}

    # Check that size is positive
    assert (df["size"] > 0).all()


def test_tips_creates_new_copy():
    """Test that tips() returns a new copy each time it's called."""
    df1 = tips()
    df2 = tips()

    # They should not be the same object
    assert df1 is not df2

    # But they should have the same data
    assert df1.equals(df2)
