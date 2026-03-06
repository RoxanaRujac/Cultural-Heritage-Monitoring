"""
Responsible for: building the AI prompt and calling the Groq API.
"""

from groq import Groq


# Move to .env in production
_GROQ_API_KEY = "miaumiau"

_SYSTEM_PROMPT = (
    "You are an expert in satellite remote sensing and cultural heritage conservation."
)

_USER_PROMPT_TEMPLATE = """You are an expert in satellite remote sensing and cultural heritage conservation.
Analyze the following change in the {index_name} index for a {context}:

- Value in Period 1: {before_mean:.4f}
- Value in Period 2: {after_mean:.4f}
- Absolute Change: {diff:.4f}

Provide a concise professional interpretation (6-7 sentences) covering:
1. What this change physically represents (e.g., vegetation growth, urban encroachment, soil erosion).
2. Potential risks to the heritage site.
3. Recommended action for conservators.

Write in a clear, informative style suitable for heritage professionals.
Use bullet points if they aid clarity, but keep it concise.
Respond in English only."""


class AIInterpreter:
    """
    Generates natural-language interpretations of spectral index changes
    using the Groq LLM API (llama-3.3-70b-versatile).

    Usage:
        interpreter = AIInterpreter()
        text = interpreter.interpret(
            index_name='NDVI',
            before_mean=0.35,
            after_mean=0.22,
            context='Alba Iulia Fortress'
        )
    """

    MODEL        = 'llama-3.3-70b-versatile'
    MAX_TOKENS   = 300
    TEMPERATURE  = 0.4
    FALLBACK_MSG = (
        "AI could not generate an interpretation for this change. "
        "Please review the data and try again."
    )

    def __init__(self, api_key: str = _GROQ_API_KEY):
        self._client = Groq(api_key=api_key)

    def interpret(
        self,
        index_name: str,
        before_mean: float,
        after_mean: float,
        context: str = 'heritage site',
    ) -> str:
        """
        Return an AI-generated interpretation string.
        Returns FALLBACK_MSG if the API call fails.

        Args:
            index_name:  Spectral index name (e.g. 'NDVI').
            before_mean: Mean index value in the earlier period.
            after_mean:  Mean index value in the later period.
            context:     Site name or description for the prompt.
        """
        prompt = _USER_PROMPT_TEMPLATE.format(
            index_name=index_name,
            context=context,
            before_mean=before_mean,
            after_mean=after_mean,
            diff=after_mean - before_mean,
        )

        try:
            response = self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {'role': 'system', 'content': _SYSTEM_PROMPT},
                    {'role': 'user',   'content': prompt},
                ],
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
            )
            content = response.choices[0].message.content if response.choices else None
            return content or self.FALLBACK_MSG
        except Exception:
            return self.FALLBACK_MSG