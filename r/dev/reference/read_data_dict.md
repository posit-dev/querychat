# Read a Data Dictionary from YAML

Loads a data dictionary from a YAML file conforming to the [data-dict
spec](https://data-dict.tidyverse.org/). The dictionary is returned as a
plain list and can be passed directly to
[QueryChat](https://posit-dev.github.io/querychat/dev/reference/QueryChat.md)
via the `data_dict` argument.

If `name` is absent from the YAML file, it defaults to the file stem.

## Usage

``` r
read_data_dict(path)
```

## Arguments

- path:

  Path to the YAML file.

## Value

A named list with the structure of the YAML file.
