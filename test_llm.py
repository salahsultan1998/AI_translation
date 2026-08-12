import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv(".env")
# Initialize client targeting OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

async def fetch_llm_response(prompt) :
    response = await client.chat.completions.create(
        # You can use any OpenRouter model identifier (e.g., anthropic/claude-3.5-sonnet, google/gemini-2.5-flash, openai/gpt-4o-mini)
        model="qwen/qwen3.7-flash",
        messages=[{"role": "user", "content": prompt}],
        # Optional OpenRouter headers for app ranking/identification

    )
    return response.choices[0].message.content

async def main():
    prompts = [
        "Explain quantum computing in one sentence.",
        "Write a haiku about rainy days.",
        "What are the top 3 soft skills for developers?",
        "Define opportunity cost in plain terms."
    ]

    # Fire all calls concurrently
    tasks = [fetch_llm_response(p) for p in prompts]
    results = await asyncio.gather(*tasks)

    for prompt, result in zip(prompts, results):
        print(f"Q: {prompt}\nA: {result}\n")

asyncio.run(main())

