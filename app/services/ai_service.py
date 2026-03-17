from typing import List

from groq import Groq
from app.core.config import settings
import re
import time
import random
from groq import Groq, RateLimitError

groq_client = Groq(api_key=settings.GROQ_API_KEY)

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

async def get_groq_completion(prompt: str, model: str = "llama-3.3-70b-versatile"):
    """
    Função genérica para chamadas ao Groq com lógica de retry (cota/erro).
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
            )
            return clean_text(response.choices[0].message.content)
            
        except RateLimitError:
            if attempt == max_retries - 1: raise
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)
        except Exception as e:
            if attempt == max_retries - 1: raise e
            time.sleep(1)

async def generate_general_report_ai_content(
    chip_id: str, 
    inicio: str, 
    fim: str, 
    total_records: int, 
    stats: dict, 
    amostra: List[float]
):
    prompt = f"""
    Gere um relatório médio, claro e sucinto sobre as temperaturas coletadas na estufa com chipId {chip_id}.
    Intervalo de coleta: {inicio} até {fim}. 
    
    Foram coletados {total_records} registros de temperatura.
    
    Estatísticas fornecidas:
    {stats}
    
    Primeiros valores coletados:
    {amostra} # apenas amostra
    
    Inclua:
    - Título curto
    - Um parágrafo de resumo
    - Lista objetiva de estatísticas
    - Curto comentário de tendência observada
    - Curto comentário em cada estatística observada

    Escreva de forma analítica e técnica, mantendo consistência numérica.
    """
    return await get_groq_completion(prompt)


async def generate_experiment_ai_content(nome: str, objetivo: str, stats: dict):
    """
    Lógica específica para montar o prompt do Laudo de Experimento.
    """
    prompt = f"""
    Aja como um especialista em biotecnologia. Analise o experimento científico: "{nome}"
    Objetivo: {objetivo}
    
    Parâmetros:
    - Faixa Ideal: {stats['min_ideal']}°C a {stats['max_ideal']}°C
    - Registros: {stats['total_records']}
    - Estabilidade: {stats['estabilidade']}% dentro da faixa.
    - Extremos: Mín {stats['min_real']}°C / Máx {stats['max_real']}°C
    - NÃO inclua campos de assinatura, nomes fictícios, cargos ou datas ao final.
    
    Gere um laudo técnico sucinto confirmando se o ambiente térmico foi adequado para o objetivo proposto.
    Aponte riscos caso a estabilidade seja baixa. Seja direto e profissional.
    """
    return await get_groq_completion(prompt)

async def generate_quick_insight(data):
    stats = data.statistics
    
    trend_arrow = " ↗️ " if stats.lastValue > stats.mean else " ↘️ "
    sampling_str = " -> ".join([f"{v:.2f}°C" for v in stats.sampling])
 
    prompt = f"""
    SISTEMA: SafeTemp - Monitoramento Térmico Inteligente.
    PAPEL: Você é um Especialista em Biotecnologia e Automação Agrícola.
    
    CONTEXTO DO USUÁRIO: "{data.text}"
    
    DADOS DE TELEMETRIA (Última Hora):
    - Média: {stats.mean:.2f}°C | Pico: {stats.max:.2f}°C | Mín: {stats.min:.2f}°C
    - Estado Atual: {stats.lastValue:.2f}°C {trend_arrow}
    - Amostragem Temporal: {sampling_str}
    - Outliers/Anomalias: {stats.outliers if stats.outliers else "Estabilidade nominal"}
    """

    if data.mode == 'experiment':
        prompt += f"""
        CONFIGURAÇÃO DO EXPERIMENTO:
        - Cultura: {data.culture} | Estágio: {data.stage}
        - Faixa Ideal: {data.thresholds.min}°C a {data.thresholds.max}°C (Crítico: {data.thresholds.criticalMax}°C)
        - Equipamento(s): {data.equipment}
        """

    prompt += """
    TAREFA: Gere uma análise técnica profissional.
    REGRAS:
    1. Use português correto e verifique o espaçamento entre as palavras.
    2. Comece com um veredito direto sobre a estabilidade.
    3. Se houver variação brusca ou outliers, aponte a causa provável baseada no contexto do usuário.
    4. NÃO use saudações, apenas o texto técnico.
    """

    return await get_groq_completion(prompt)