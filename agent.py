import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()


def analyze_incident(incident, memories):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing in .env")
    client = Groq(api_key=GROQ_API_KEY)
    memory_text = "\n\n".join(
        f"Historical Incident {i}: {memory}" for i, memory in enumerate(memories, 1)
    ) or "No relevant historical incidents were found."
    prompt = f"""You are an Incident Response Agent for an IT operations team.

CURRENT INCIDENT
{incident}

HISTORICAL MEMORY FROM HINDSIGHT
{memory_text}

Use memory as evidence. Do not invent historical incidents, fixes, outcomes,
dates, commands, versions, or infrastructure details.

Return exactly:
### Incident Summary
### Similar Historical Incidents
### Previous Resolutions
### Recommended Response
### Information Gap

Keep it concise and practical."""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional IT incident response analyst."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
