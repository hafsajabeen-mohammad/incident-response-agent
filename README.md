# Incident Response Agent

AI-powered incident investigation using Hindsight persistent memory and Groq.

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Configure keys

Copy `.env.example` to `.env` and add your own keys:

```env
HINDSIGHT_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=hsk_...
HINDSIGHT_BANK_ID=incident-response
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
```

## 3. Load the historical dataset into Hindsight

Run this once:

```bash
python load_data.py
```

If your Hindsight bank already contains the dataset, you do not need to run it again.

## 4. Start the app

```bash
streamlit run app.py
```

## Features

- Hindsight retain + recall
- Incident investigation with historical memory
- Groq `openai/gpt-oss-20b`
- Clickable Report Incident / Incident History navigation
- Searchable incident history
- No invented incident dates
- Cleans HTML accidentally stored by older versions
- Avoids the previous circular import
- Safe async Hindsight client handling
