from fastapi import FastAPI, Request
from google import genai
import time
import random
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import re
from google.api_core import exceptions

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
- Datas do intervalo fornecido convertidas em fuso BRT -3, limpando a string ISO para apenas o horário.

Escreva de forma analítica e técnica, mantendo consistência numérica.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
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
        except exceptions.ResourceExhausted as e: 
            print(f"Cota excedida (Erro 429). Tentativa {attempt + 1} de {max_retries}. Aguardando...")
            
            if attempt == max_retries - 1:
                print("Esgotadas todas as tentativas de cota.")
                return JSONResponse(status_code=429, content={"erro": "Cota de IA excedida. Tente mais tarde."})

            wait_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)

        except Exception as e:
            print(f"Erro genérico na tentativa {attempt + 1}: {e}")

            if attempt == max_retries - 1:
                return JSONResponse(status_code=500, content={"erro": f"Erro interno na IA: {str(e)}"})

            time.sleep(1)