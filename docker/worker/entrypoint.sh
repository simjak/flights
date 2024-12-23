#!/bin/bash
set -e

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Run the worker process
exec python -m src.worker.main