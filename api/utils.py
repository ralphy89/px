def strip_markdown_fences(text: str) -> str:
    """
    Remove ```json ... ``` or ``` ... ``` blocks from model output.
    """
    # Remove ```json ... ``` and ``` ... ```
    text = text.strip()

    if text.startswith("```"):
        # Remove starting fence (``` or ```json)
        first_newline = text.find("\n")
        text = text[first_newline+1:]

    if text.endswith("```"):
        text = text[: -3]

    return text.strip()