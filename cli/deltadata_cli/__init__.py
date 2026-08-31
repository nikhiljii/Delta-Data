"""DeltaData CLI -- talks to the DeltaData /api/v1/compare API.

This package never reimplements the analysis engine: every `compare` call is
a plain HTTP request to a running DeltaData API instance.
"""

__version__ = "0.1.2"
