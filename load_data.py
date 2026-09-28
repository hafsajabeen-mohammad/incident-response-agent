import os
import pandas as pd
from hindsight_memory import save_memory

CSV_FILE = os.path.join(os.path.dirname(__file__), "data", "tickets.csv")
MAX_INCIDENTS = int(os.getenv("MAX_INCIDENTS", "300"))


def load_incidents():
    df = pd.read_csv(CSV_FILE).fillna("")
    df = df[(df["type"].str.lower() == "incident") & (df["language"].str.lower() == "en")]
    if MAX_INCIDENTS > 0:
        df = df.head(MAX_INCIDENTS)
    print(f"Found {len(df)} English incidents to store in Hindsight.")

    for count, (_, row) in enumerate(df.iterrows(), 1):
        tags = ", ".join(str(row[f"tag_{i}"]) for i in range(1, 10) if str(row[f"tag_{i}"]).strip())
        memory = f"""Incident Record
Type: {row['type']}
Priority: {row['priority']}
Queue: {row['queue']}
Subject: {row['subject']}
Description: {row['body']}
Previous Resolution / Support Response: {row['answer']}
Business Type: {row['business_type']}
Tags: {tags}"""
        save_memory(memory)
        print(f"Stored {count}/{len(df)}")

    print("Done. Historical incidents are now in Hindsight.")


if __name__ == "__main__":
    load_incidents()
