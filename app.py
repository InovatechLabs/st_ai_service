from fastapi import FastAPI, Request
from google import genai
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os
import re

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

def clean_text(text: str) -> str:
    if not text:
        return text

    # Remove títulos markdown (###, ##, #)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    # Remove bold/itens: **texto**, *texto*
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # Remove listas "- "
    text = re.sub(r"^-+\s*", "", text, flags=re.MULTILINE)

    # Remove separadores tipo "---"
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)

    # Converte múltiplas quebras de linha em apenas uma
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()

@app.get("/")
def root():
    return {"status": "ok", "message": "Serviço de IA ativo"}

@app.post("/gerar-report")
async def generate_report(request: Request):
    body = await request.json()
    records = body.get("records", [])
    statistics = body.get("statistics") or {}

    if not records:
        return {"erro": "Nenhum dado recebido"}
    
    valores = [r["value"] for r in records if "value" in r]
    chip_id = records[0].get("chipId", "desconhecido") if records else "desconhecido"
    timestamps = [r["timestamp"] for r in records if "timestamp" in r]

    inicio = timestamps[0] if timestamps else "desconhecido"
    fim = timestamps[-1] if timestamps else "desconhecido"

    if not statistics and valores:
    
        media = sum(valores) / len(valores)
        statistics = {"media": media, "min": min(valores), "max": max(valores), "desvioPadrao": None}

    
    prompt = f"""
    Gere um relatório médio, claro e sucinto sobre as temperaturas coletadas na estufa com chipId {chip_id}.
    Intervalo de coleta: {inicio} até {fim}.
    
    Foram coletados {len(records)} registros de temperatura.
    
    Estatísticas fornecidas:
    {statistics}
    
    Primeiros valores coletados:
    {valores[:10]}  # apenas amostra
    
 Inclua:
- Título curto
- Um parágrafo de resumo
- Lista objetiva de estatísticas
- Curto comentário de tendência observada
- Curto comentário em cada estatística observada

Escreva de forma analítica e técnica, mantendo consistência numérica.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    texto_limpo = clean_text(response.text)
    return {
        "relatorio": texto_limpo,
        "resumo": {
            "intervalo": f"{inicio} → {fim}",
            "registros": len(records),
            "media": statistics.get("media"),
            "min": statistics.get("min"),
            "max": statistics.get("max"),
            "std": statistics.get("desvioPadrao"),
            "variancia": statistics.get("variancia"),
            "cvoutlier": statistics.get("CVOutlier"),
            "cvnooutlier": statistics.get("CVNoOutlier"),
            "registros": statistics.get("totalRecords"),
            "totalOutliers": statistics.get("totalOutliers")
        }
    }