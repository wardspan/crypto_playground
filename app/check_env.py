import os
from typing import List

required_vars = [
    'DATABASE_URL',
    'JWT_SECRET_KEY',
    'JWT_ALGORITHM',
    'ACCESS_TOKEN_EXPIRE_MINUTES',
    'SMTP_SERVER',
    'SMTP_PORT',
    'EMAIL_USERNAME',
    'EMAIL_PASSWORD',
    'COINGECKO_API_KEY'
]

def check_env_vars(vars: List[str]) -> bool:
    missing_vars = []
    for var in vars:
        if var not in os.environ:
            missing_vars.append(var)
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        return False
    return True 