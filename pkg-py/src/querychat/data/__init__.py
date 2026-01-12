"""
Sample datasets for getting started with querychat.

This module provides easy access to sample datasets that can be used with QueryChat
to quickly get started without needing to install additional dependencies.
"""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

from querychat._df_compat import read_csv

if TYPE_CHECKING:
    import narwhals.stable.v1 as nw


def titanic() -> nw.DataFrame:
    """
    Load the Titanic dataset.

    This dataset contains information about passengers on the Titanic, including
    whether they survived, their class, age, sex, and other demographic information.

    Returns
    -------
    :
        A narwhals DataFrame with 891 rows and 15 columns containing Titanic
        passenger data.

    Examples
    --------
    >>> from querychat.data import titanic
    >>> from querychat import QueryChat
    >>> df = titanic()
    >>> qc = QueryChat(df, "titanic")
    >>> app = qc.app()

    """
    # Get the path to the gzipped CSV file using importlib.resources
    data_file = files("querychat.data") / "titanic.csv.gz"
    return read_csv(str(data_file))


def tips() -> nw.DataFrame:
    """
    Load the tips dataset.

    This dataset contains information about restaurant tips, including the total
    bill, tip amount, and information about the party (sex, smoker status, day,
    time, and party size).

    Returns
    -------
    :
        A narwhals DataFrame with 244 rows and 7 columns containing restaurant
        tip data.

    Examples
    --------
    >>> from querychat.data import tips
    >>> from querychat import QueryChat
    >>> df = tips()
    >>> qc = QueryChat(df, "tips")
    >>> app = qc.app()

    """
    # Get the path to the gzipped CSV file using importlib.resources
    data_file = files("querychat.data") / "tips.csv.gz"
    return read_csv(str(data_file))


__all__ = ["tips", "titanic"]
