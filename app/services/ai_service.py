import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def classify_and_solve_issue(message: str, model: str = "llama3.2") -> dict:
    prompt = f"""
    Eres NEXO AI, un copiloto empresarial inteligente, pero también un compañero empático y comprensivo con los operadores.
    Si el usuario te cuenta un problema personal (como que terminó con su novia, está triste, cansado, o cosas de la vida):
    - Sé sumamente empático, humano y dale palabras de aliento o un consejo amistoso en el "diagnostico_breve" y la "solucion_sugerida".
    - No des respuestas frías ni robóticas como "Procesado correctamente". Involúcrate emocionalmente como un buen colega.
    - Asigna categoría "Personal", prioridad "Baja", y departamento "General".

    Responde ÚNICAMENTE con un objeto JSON válido, sin texto fuera de él.
    Usa exactamente esta estructura de claves:
    {{
        "categoria": "Soporte Técnico | Infraestructura | Facturación | Desarrollo | Consulta General | Personal",
        "prioridad": "Baja | Media | Alta | Crítica",
        "departamento_responsable": "Sistemas | Redes | Desarrollo | Atención al Cliente | Administración | General",
        "diagnostico_breve": "Tu respuesta empática, consejo o comentario humano ante la situación del usuario",
        "solucion_sugerida": "Un consejo práctico, palabras de apoyo o una recomendación para despejarse"
    }}

    Mensaje del usuario: "{message}"
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.7,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        raw_response = response.json().get("response", "{}")

        clean_response = raw_response.replace("```json", "").replace("```", "").strip()
        structured_data = json.loads(clean_response)
        return structured_data

    except json.JSONDecodeError:
        return {
            "categoria": "Personal",
            "prioridad": "Baja",
            "departamento_responsable": "General",
            "diagnostico_breve": raw_response[:250] if 'raw_response' in locals() else "¡Ánimo! Aquí andamos para platicar.",
            "solucion_sugerida": "Tómate un respiro, sal a despejarte un momento."
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Error de conexión con Ollama: {str(e)}"}