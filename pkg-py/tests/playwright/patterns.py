"""Shared regex patterns for querychat Playwright tests."""

import re

# SQL WHERE clause patterns
SQL_FEMALE_FILTER = re.compile(r"WHERE.*sex.*=.*['\"]?female['\"]?", re.IGNORECASE)
SQL_MALE_FILTER = re.compile(r"WHERE.*sex.*=.*['\"]?male['\"]?", re.IGNORECASE)

SQL_SURVIVED_FILTER = re.compile(r"WHERE.*survived.*=.*(1|TRUE)", re.IGNORECASE)
SQL_FIRST_CLASS_FILTER = re.compile(
    r"WHERE.*(p?class).*=.*(1|['\"]First['\"])", re.IGNORECASE
)

# Chat response patterns
RESPONSE_SURVIVAL = re.compile(r"(surviv\w*.*\d+|\d+.*surviv\w*)", re.IGNORECASE)
RESPONSE_AGE = re.compile(r"(age.*\d+\.?\d*|\d+\.?\d*.*age|average.*\d+)", re.IGNORECASE)
RESPONSE_FARE = re.compile(r"(fare.*\d+\.?\d*|\d+\.?\d*.*fare|average.*\d+)", re.IGNORECASE)
RESPONSE_CLASS = re.compile(
    r"(class.*\d+|\d+.*(first|second|third)|count.*class)", re.IGNORECASE
)
RESPONSE_FIRST_CLASS = re.compile(r"first.class|class.1|first.class.passenger", re.IGNORECASE)
RESPONSE_FILTER = re.compile(r"filter|showing|display|first.class", re.IGNORECASE)
RESPONSE_MALE_FILTER = re.compile(r"male.passenger|filter.*male|showing.*male", re.IGNORECASE)

# Greeting/suggestion patterns
GREETING_SUGGESTIONS = re.compile(r"survived|class|age", re.IGNORECASE)
GREETING_SUGGESTIONS_FULL = re.compile(
    r"survived|class|age|passenger", re.IGNORECASE
)
GREETING_SUGGESTIONS_FILTER = re.compile(
    r"survived|class|age|passenger|filter", re.IGNORECASE
)
