from langchain_core.tools import tool
from openai import AsyncOpenAI

from app.config import settings

client = AsyncOpenAI()


@tool
async def search_public_web(query: str) -> str:
    """Search the live public web for current events, news, and schedules."""
    response = await client.responses.create(
        model=settings.model_name,
        tools=[{"type": "web_search"}],
        input=query,
    )
    return response.output_text
