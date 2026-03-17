from fastapi import APIRouter, Depends, HTTPException
from app.services import ai_service
from app.api.deps import validate_internal_token
from app.schemas.reports import ExperimentReportRequest 
from app.schemas.reports import ReportRequest

router = APIRouter()

@router.post("/gerar-laudo-experimento")
async def generate_experiment_report(data: ExperimentReportRequest, token=Depends(validate_internal_token)):
    valores = [r.value for r in data.records]
    fora_da_faixa = [v for v in valores if v < data.metadata.min or v > data.metadata.max]
    percentual = ((len(valores) - len(fora_da_faixa)) / len(valores)) * 100

    stats_for_ai = {
        "min_ideal": data.metadata.min,
        "max_ideal": data.metadata.max,
        "min_real": min(valores),
        "max_real": max(valores),
        "total_records": len(valores),
        "estabilidade": f"{percentual:.1f}",
        "objetivo": data.metadata.objetivo,
        "nome": data.metadata.nome
    }

    try:
        laudo = await ai_service.generate_experiment_ai_content(
            data.metadata.nome, 
            data.metadata.objetivo, 
            stats_for_ai
        )
        
        return {
            "laudo": laudo,
            "estatisticas": {
                "estabilidade": f"{percentual:.1f}%",
                "total_registros": len(valores),
                "fora_da_faixa": len(fora_da_faixa)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento de IA: {str(e)}")
    
@router.post("/gerar-report")
async def generate_report(data: ReportRequest, token: dict = Depends(validate_internal_token)):
    if not data.records:
        raise HTTPException(status_code=400, detail="Nenhum dado recebido")

    valores = [r.value for r in data.records]
    chip_id = data.records[0].chipId
    inicio = data.records[0].timestamp
    fim = data.records[-1].timestamp
    
    stats_dict = data.statistics.dict() if data.statistics else {}
    if not data.statistics and valores:
        stats_dict = {
            "media": sum(valores) / len(valores),
            "min": min(valores),
            "max": max(valores),
            "desvioPadrao": None
        }

    try:
        relatorio_texto = await ai_service.generate_general_report_ai_content(
            chip_id=chip_id,
            inicio=inicio,
            fim=fim,
            total_records=len(valores),
            stats=stats_dict,
            amostra=valores[:10]
        )
        
        return {
            "relatorio": relatorio_texto,
            "resumo": {
                "intervalo": f"{inicio} → {fim}",
                "registros": len(valores),
                **stats_dict 
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar relatório: {str(e)}")