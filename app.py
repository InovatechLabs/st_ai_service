from fastapi import FastAPI, Request
from google import genai
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@app.get("/")
def root():
    return {"status": "ok", "message": "Serviço de IA ativo"}

@app.post("/gerar-report")
async def generate_report(request: Request):
    body = await request.json()
    records = body.get("records", [])
    statistics = body.get("statistics", "Estatísticas não fornecidas")

    if not records:
        return {"erro": "Nenhum dado recebido"}
    
    valores = [r["value"] for r in records if "value" in r]
    chip_id = records[0].get("chipId", "desconhecido") if records else "desconhecido"
    timestamps = [r["timestamp"] for r in records if "timestamp" in r]

    inicio = timestamps[0] if timestamps else "desconhecido"
    fim = timestamps[-1] if timestamps else "desconhecido"

    if not statistics and valores:
    
        media = sum(valores) / len(valores)
        statistics = {"media": media, "min": min(valores), "max": max(valores)}
    
    prompt = f"""
    Gere um relatório técnico sobre as temperaturas coletadas na estufa com chipId {chip_id}.
    Intervalo de coleta: {inicio} até {fim}.
    
    Foram coletados {len(records)} registros de temperatura.
    
    Estatísticas fornecidas:
    {statistics}
    
    Primeiros valores coletados:
    {valores[:10]}  # apenas amostra
    
    Analise as estatísticas de temperatura fornecidas. Responda apenas com os seguintes 4 pontos,
    de forma direta e telegráfica (Sem textos introdutórios):
    - Variação: [Mínima]°C a [Máxima]°C (Delta: [X]°C)
    - Anomalias: [Não detectadas / Listar valores anômalos]
    - Tendência: [Aquecimento / Resfriamento / Estável]
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return {
        "relatorio": response.text,
        "resumo": {
            "intervalo": f"{inicio} → {fim}",
            "registros": len(records),
            "media": statistics.get("media"),
            "min": statistics.get("min"),
            "max": statistics.get("max")
        }
    }