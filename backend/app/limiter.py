"""Rate limiter shared instance."""
from slowapi import Limiter  # type: ignore
from slowapi.util import get_remote_address  # type: ignore

# Shared limiter instance. Default limits can be configured here if desired.
limiter = Limiter(key_func=get_remote_address)
