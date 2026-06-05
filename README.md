# Conda_Financial_Modeling
Financial Forecast Model using Anaconda for Python


## NEXUS AI Provider Setup

`nexus_ai.py` now supports both Anthropic and Gemini providers.

- Anthropic (default): set `ANTHROPIC_API_KEY`
- Gemini: set `GEMINI_API_KEY` or pass `--api-key`

Examples:

```bash
python nexus_ai.py ask "Summarize risk" --provider anthropic
python nexus_ai.py ask "Summarize risk" --provider gemini --api-key "$GEMINI_API_KEY"
```

> Note: GhostRecon tool execution (`--tools`) is currently supported with Anthropic provider only.
