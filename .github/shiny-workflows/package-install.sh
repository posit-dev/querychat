#!/bin/bash

# ggsql (Suggests) requires unixODBC to compile from source on macOS
if [ "$RUNNER_OS" == "macOS" ]; then
  brew install unixodbc
fi
