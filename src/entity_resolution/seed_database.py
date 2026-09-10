"""
Seed Knowledge Base: 50 Known Canonical AI Startups & Organizations
(Phase IV: Deterministic Entity Resolution)
"""

from typing import Dict, List, Set, Any

SEED_CANONICAL_STARTUPS: Dict[str, Dict[str, Any]] = {
    "OpenAI": {
        "domain": "openai.com",
        "aliases": ["OpenAI", "OpenAI, Inc.", "Open AI", "OpenAI LLC", "OpenAI Global LLC", "OpenAI OpCo LLC"]
    },
    "Anthropic": {
        "domain": "anthropic.com",
        "aliases": ["Anthropic", "Anthropic, PBC", "Anthropic PBC", "Anthropic AI"]
    },
    "Cohere": {
        "domain": "cohere.com",
        "aliases": ["Cohere", "Cohere Inc.", "Cohere AI"]
    },
    "Mistral AI": {
        "domain": "mistral.ai",
        "aliases": ["Mistral", "Mistral AI", "Mistral SAS", "Mistral AI Inc."]
    },
    "Hugging Face": {
        "domain": "huggingface.co",
        "aliases": ["Hugging Face", "HuggingFace", "Hugging Face, Inc.", "HuggingFace Inc."]
    },
    "Perplexity AI": {
        "domain": "perplexity.ai",
        "aliases": ["Perplexity", "Perplexity AI", "Perplexity, Inc.", "Perplexity AI, Inc."]
    },
    "Stability AI": {
        "domain": "stability.ai",
        "aliases": ["Stability AI", "StabilityAI", "Stability AI Ltd.", "Stability AI Inc."]
    },
    "Scale AI": {
        "domain": "scale.com",
        "aliases": ["Scale AI", "Scale", "Scale AI, Inc.", "Scale Media"]
    },
    "ElevenLabs": {
        "domain": "elevenlabs.io",
        "aliases": ["ElevenLabs", "Eleven Labs", "ElevenLabs Inc.", "Eleven Labs, Inc."]
    },
    "Runway": {
        "domain": "runwayml.com",
        "aliases": ["Runway", "RunwayML", "Runway AI, Inc.", "Runway Research"]
    },
    "Google DeepMind": {
        "domain": "deepmind.google",
        "aliases": ["DeepMind", "Deep Mind", "Google DeepMind", "DeepMind Technologies Ltd."]
    },
    "Midjourney": {
        "domain": "midjourney.com",
        "aliases": ["Midjourney", "Midjourney, Inc.", "Midjourney Inc."]
    },
    "Jasper": {
        "domain": "jasper.ai",
        "aliases": ["Jasper", "Jasper AI", "Jasper AI, Inc.", "Jarvis.ai"]
    },
    "Inflection AI": {
        "domain": "inflection.ai",
        "aliases": ["Inflection", "Inflection AI", "Inflection AI, Inc."]
    },
    "Character.AI": {
        "domain": "character.ai",
        "aliases": ["Character.AI", "Character AI", "Character Technologies, Inc."]
    },
    "Synthesia": {
        "domain": "synthesia.io",
        "aliases": ["Synthesia", "Synthesia Ltd.", "Synthesia AI"]
    },
    "Anysphere (Cursor)": {
        "domain": "cursor.com",
        "aliases": ["Cursor", "Anysphere", "Anysphere, Inc.", "Cursor AI"]
    },
    "Glean": {
        "domain": "glean.com",
        "aliases": ["Glean", "Glean Technologies, Inc.", "Glean Technologies"]
    },
    "Pinecone": {
        "domain": "pinecone.io",
        "aliases": ["Pinecone", "Pinecone Systems, Inc.", "Pinecone Database"]
    },
    "LangChain": {
        "domain": "langchain.com",
        "aliases": ["LangChain", "LangChain, Inc.", "LangChain AI"]
    },
    "LlamaIndex": {
        "domain": "llamaindex.ai",
        "aliases": ["LlamaIndex", "Llama Index", "LlamaIndex Inc."]
    },
    "Weaviate": {
        "domain": "weaviate.io",
        "aliases": ["Weaviate", "Weaviate B.V.", "SeMI Technologies"]
    },
    "Qdrant": {
        "domain": "qdrant.tech",
        "aliases": ["Qdrant", "Qdrant Solutions GmbH"]
    },
    "Together AI": {
        "domain": "together.ai",
        "aliases": ["Together AI", "Together.ai", "Together Computer Inc."]
    },
    "Replicate": {
        "domain": "replicate.com",
        "aliases": ["Replicate", "Replicate, Inc.", "Replicate AI"]
    },
    "Fireworks AI": {
        "domain": "fireworks.ai",
        "aliases": ["Fireworks AI", "Fireworks.ai", "Fireworks"]
    },
    "Groq": {
        "domain": "groq.com",
        "aliases": ["Groq", "Groq, Inc.", "Groq Inc."]
    },
    "Harvey": {
        "domain": "harvey.ai",
        "aliases": ["Harvey", "Harvey AI", "Counsel AI Corp."]
    },
    "Writer": {
        "domain": "writer.com",
        "aliases": ["Writer", "Writer, Inc.", "Writer.com", "Qordoba"]
    },
    "Adept AI": {
        "domain": "adept.ai",
        "aliases": ["Adept", "Adept AI", "Adept AI Labs Inc."]
    },
    "Covariant": {
        "domain": "covariant.ai",
        "aliases": ["Covariant", "Covariant.ai", "Covariant AI"]
    },
    "Figure AI": {
        "domain": "figure.ai",
        "aliases": ["Figure", "Figure AI", "Figure AI, Inc."]
    },
    "Physical Intelligence": {
        "domain": "physicalintelligence.company",
        "aliases": ["Physical Intelligence", "pi", "pi.company"]
    },
    "Poolside": {
        "domain": "poolside.ai",
        "aliases": ["Poolside", "Poolside AI", "Poolside SAS"]
    },
    "Decagon": {
        "domain": "decagon.ai",
        "aliases": ["Decagon", "Decagon AI", "Decagon Inc."]
    },
    "Sierra": {
        "domain": "sierra.ai",
        "aliases": ["Sierra", "Sierra AI", "Sierra Technologies"]
    },
    "Cresta": {
        "domain": "cresta.com",
        "aliases": ["Cresta", "Cresta AI", "Cresta Intelligence Inc."]
    },
    "Tabnine": {
        "domain": "tabnine.com",
        "aliases": ["Tabnine", "Tabnine Inc.", "Codota"]
    },
    "Codeium": {
        "domain": "codeium.com",
        "aliases": ["Codeium", "Exafunction", "Exafunction, Inc."]
    },
    "Pika": {
        "domain": "pika.art",
        "aliases": ["Pika", "Pika Labs", "Pika Labs Inc.", "Pika AI"]
    },
    "Suno": {
        "domain": "suno.ai",
        "aliases": ["Suno", "Suno AI", "Suno, Inc."]
    },
    "Udio": {
        "domain": "udio.com",
        "aliases": ["Udio", "Udio AI", "Uncharted Labs, Inc."]
    },
    "Phind": {
        "domain": "phind.com",
        "aliases": ["Phind", "Phind AI", "HelloCognition Inc."]
    },
    "Tavily": {
        "domain": "tavily.com",
        "aliases": ["Tavily", "Tavily AI"]
    },
    "Unstructured": {
        "domain": "unstructured.io",
        "aliases": ["Unstructured", "Unstructured Technologies Inc.", "Unstructured.io"]
    },
    "Modal": {
        "domain": "modal.com",
        "aliases": ["Modal", "Modal Labs", "Modal Labs Inc."]
    },
    "Lambda Labs": {
        "domain": "lambdalabs.com",
        "aliases": ["Lambda", "Lambda Labs", "Lambda, Inc."]
    },
    "Crusoe Energy": {
        "domain": "crusoeenergy.com",
        "aliases": ["Crusoe", "Crusoe Energy", "Crusoe Energy Systems LLC"]
    },
    "Cerebras Systems": {
        "domain": "cerebras.net",
        "aliases": ["Cerebras", "Cerebras Systems", "Cerebras Systems Inc."]
    },
    "SambaNova Systems": {
        "domain": "sambanova.ai",
        "aliases": ["SambaNova", "SambaNova Systems", "SambaNova Systems, Inc."]
    }
}
