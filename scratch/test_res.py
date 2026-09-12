import asyncio
from src.llm.orchestrator import LLMOrchestrator

async def main():
    o = LLMOrchestrator()
    schema = 'JSON: {"canonical_name": "Apple", "confidence": 0.95, "is_recognized": true}'
    prompt = "Input entity: 'appole'. If this is a typo or variation of a real tech company/startup, output the canonical name."
    res, tier = await o.extract(prompt, schema)
    print("Tier:", tier)
    print("Result:", res)

if __name__ == '__main__':
    asyncio.run(main())
