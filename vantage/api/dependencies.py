from fastapi import Depends
from vantage.core.security import verify_api_key

require_api_key = Depends(verify_api_key)
