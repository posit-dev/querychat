# querychat <a href="https://posit-dev.github.io/querychat/py/"><img src="https://posit-dev.github.io/querychat/images/querychat.png" align="right" height="138" alt="querychat website" /></a>

<p>
<!-- badges start -->
<a href="https://pypi.org/project/querychat/"><img alt="PyPI" src="https://img.shields.io/pypi/v/querychat?logo=python&logoColor=white&color=orange"></a>
<a href="https://choosealicense.com/licenses/mit/"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License"></a>
<a href="https://pypi.org/project/querychat"><img src="https://img.shields.io/pypi/pyversions/querychat.svg" alt="versions"></a>
<a href="https://github.com/posit-dev/querychat"><img src="https://github.com/posit-dev/querychat/actions/workflows/test.yml/badge.svg?branch=main" alt="Python Tests"></a>
<!-- badges end -->
</p>


QueryChat facilitates safe and reliable natural language exploration of tabular data, powered by SQL and large language models (LLMs). For analysts, it offers an intuitive web application where they can quickly ask questions of their data and receive verifiable data-driven answers. For software developers, QueryChat provides a comprehensive Python API to access core functionality -- including chat UI, generated SQL statements, resulting data, and more. This capability enables the seamless integration of natural language querying into bespoke data applications.

## Installation

Install the latest stable release [from PyPI](https://pypi.org/project/querychat/):

```bash
pip install querychat
```

## Quick start

The main entry point is the [`QueryChat` class](https://posit-dev.github.io/querychat/py/reference/QueryChat.html). It requires a [data source](https://posit-dev.github.io/querychat/py/data-sources.html) (e.g., pandas, polars, etc) and a name for the data.

```python
from querychat import QueryChat
from querychat.data import titanic

qc = QueryChat(titanic(), "titanic")
app = qc.app()
# app.run()
```

<p align="center">
  <img src="docs/images/quickstart.png" alt="QueryChat interface showing natural language queries" width="85%">
</p>

## Custom apps

Build your own custom web apps with natural language querying capabilities, such as [this one](https://github.com/posit-conf-2025/llm/blob/main/_solutions/25_querychat/25_querychat_02-end-app.R) which provides a bespoke interface for exploring Airbnb listings:

<p align="center">
  <img src="docs/images/airbnb.png" alt="A custom app for exploring Airbnb listings, powered by QueryChat." width="85%">
</p>

## Learn more

See the [website](https://posit-dev.github.io/querychat/py) to learn more.
