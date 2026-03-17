from fastapi import APIRouter, Depends, HTTPException
from app.schemas.context import InsightRequest
from app.api.deps import validate_internal_token
from app.services import ai_service

router = APIRouter()

@router.post("/gerar-insight")
async def generate_insight(data: InsightRequest, token: dict = Depends(validate_internal_token)):
    try:
        insight_texto = await ai_service.generate_quick_insight(data)
        
        return {
            "insight": insight_texto
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na IA: {str(e)}")