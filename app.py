from fastapi import FastAPI, Header, HTTPException, Depends, Request
from google import genai
import time
import random
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import re
from google.api_core import exceptions
from groq import Groq
from groq import InternalServerError, RateLimitError

import jwt

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = "HS256"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def validate_internal_token(authorization: str = Header(None)):
    """
    Valida o token JWT enviado no Header Authorization: Bearer <token>
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Acesso não autorizado: Token ausente ou formato inválido"
        )

    token = authorization.split(" ")[1]
    
    try:
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("service") != "safetemp-api":
            raise HTTPException(status_code=403, detail="Serviço de origem não identificado")
            
        return payload 

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado (30s de validade excedidos)")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido ou assinatura corrompida")

@app.post("/gerar-laudo-experimento")
async def generate_experiment_report(request: Request, token_data: dict = Depends(validate_internal_token)):
    body = await request.json()
    records = body.get("records", [])
    metadata = body.get("metadata", {}) 
    
    if not records:
        return {"erro": "Dados de temperatura ausentes"}

    valores = [r["value"] for r in records if "value" in r]
    temp_min = metadata.get("min")
    temp_max = metadata.get("max")
    objetivo = metadata.get("objetivo")
    nome = metadata.get("nome")

    # Lógica de estabilidade para o prompt
    fora_da_faixa = [v for v in valores if v < temp_min or v > temp_max]
    percentual_estabilidade = ((len(valores) - len(fora_da_faixa)) / len(valores)) * 100

    prompt = f"""
    Aja como um especialista em biotecnologia. Analise o experimento científico: "{nome}"
    Objetivo: {objetivo}
    
    Parâmetros:
    - Faixa Ideal: {temp_min}°C a {temp_max}°C
    - Registros: {len(records)}
    - Estabilidade: {percentual_estabilidade:.1f}% dentro da faixa.
    - Extremos: Mín {min(valores)}°C / Máx {max(valores)}°C
    - NÃO inclua campos de assinatura, nomes fictícios, cargos ou datas ao final.
    
    Gere um laudo técnico sucinto confirmando se o ambiente térmico foi adequado para o objetivo proposto.
    Aponte riscos caso a estabilidade seja baixa. Seja direto e profissional.
    """

    try:
        # Chamada para o Groq usando Llama 3
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile", 
        )
        
        laudo_texto = chat_completion.choices[0].message.content
        
        return {
            "laudo": clean_text(laudo_texto),
            "estatisticas": {
                "estabilidade": f"{percentual_estabilidade:.1f}%",
                "total_registros": len(records),
                "fora_da_faixa": len(fora_da_faixa)
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": f"Erro no Groq: {str(e)}"})

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
async def generate_report(request: Request, token_data: dict = Depends(validate_internal_token)):
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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile", 
        )
            
            texto_limpo = clean_text(response.choices[0].message.content)
            
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
        except RateLimitError as e: 
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