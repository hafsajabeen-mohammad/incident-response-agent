import asyncio
import os
import threading
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "https://api.hindsight.vectorize.io").strip()
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "").strip()
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incident-response").strip()


def _check_config():
    if not HINDSIGHT_API_KEY:
        raise RuntimeError("HINDSIGHT_API_KEY is missing in .env")
    if not HINDSIGHT_API_KEY.startswith("hsk_"):
        raise RuntimeError("HINDSIGHT_API_KEY must start with hsk_")
    if not HINDSIGHT_URL:
        raise RuntimeError("HINDSIGHT_URL is missing in .env")


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result, error = [], []
    def runner():
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:
            error.append(exc)
    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result[0]


async def _ensure_bank(client):
    try:
        await client.acreate_bank(
            bank_id=BANK_ID,
            name="Incident Response",
            background=(
                "Memory bank for IT incident response. Stores technical incidents, "
                "symptoms, root causes, previous resolutions and troubleshooting steps."
            ),
            retain_mission=(
                "Focus on technical incident symptoms, affected systems, root causes, "
                "resolutions, troubleshooting steps and outcomes."
            ),
            reflect_mission=(
                "Help an incident responder use historical incidents to investigate "
                "new technical incidents without inventing facts."
            ),
        )
    except Exception as exc:
        # A bank may already exist. Only suppress the normal duplicate/already-exists case.
        msg = str(exc).lower()
        if "already" not in msg and "exist" not in msg and "409" not in msg:
            raise


async def _save_memory_async(content):
    _check_config()
    client = Hindsight(base_url=HINDSIGHT_URL, api_key=HINDSIGHT_API_KEY)
    try:
        await _ensure_bank(client)
        return await client.aretain(bank_id=BANK_ID, content=content, context="IT incident response")
    finally:
        await client.aclose()


def save_memory(content):
    return _run_async(_save_memory_async(content))


async def _get_memory_async(query, max_tokens=4096):
    _check_config()
    client = Hindsight(base_url=HINDSIGHT_URL, api_key=HINDSIGHT_API_KEY)
    try:
        await _ensure_bank(client)
        result = await client.arecall(
            bank_id=BANK_ID,
            query=query,
            max_tokens=max_tokens,
            budget="mid",
        )
        return result.results
    finally:
        await client.aclose()


def get_memory(query, max_tokens=4096):
    return _run_async(_get_memory_async(query, max_tokens=max_tokens))
