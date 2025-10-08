def extract_json_from_text(text: str) -> str:
    """Extract the JSON snippet enclosed within a fenced ```json code block.

    Given the text in the following format:

    ```json
    {
        "key": "value"
    }
    ```

    This method extracts the json string and returns it, e.g.:
    {
        "key": "value"
    }

    Args:
        text (str): The input text containing a JSON object.

    Returns:
        str: The JSON string found inside the fenced block, or the original
            text if the block is not present.
    """

    start_marker = "```json"
    end_marker = "```"

    start_index = text.find(start_marker)
    if start_index == -1:
        return text.strip()

    start_index += len(start_marker)

    end_index = text.find(end_marker, start_index)
    if end_index == -1:
        return text[start_index:].strip()

    return text[start_index:end_index].strip()
