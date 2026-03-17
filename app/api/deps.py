from fastapi import Header, HTTPException
import jwt
from app.core.config import settings

def validate_internal_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Acesso não autorizado: Token ausente"
        )

    token = authorization.split(" ")[1]
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        if payload.get("service") != "safetemp-api":
            raise HTTPException(status_code=403, detail="Origem inválida")
            
        return payload 

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")