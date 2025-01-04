from minerva.llm.client import Client


def generate_filename(
    client: Client, 
    text: str, 
    model_name: str = "claude-3-5-sonnet-latest",
    temperature: float = 0.3,
    max_tokens: int = 4096,
    ext: str = ".yml"
) -> str:
    """
    Generate a file name as a summary of the given text.

    Args:
        client: Client
        text: str
        model_name: str = "claude-3-5-sonnet-latest"
        temperature: float = 0.3
        max_tokens: int = 4096
        ext: str = ".yml"

    Returns:
        A file name as a summary of the given text.
    """
    prompt: str = f"""
    Given the following text, generate a concise and clear file name that summarizes the key
    content in a format appropriate for saving as a file. The file name should be brief, avoid
    special characters (except hyphens or underscores), and reflect the primary topic or
    purpose of the text. It should be clear and recognizable, such that someone can infer the
    content of the file without opening it.

    <Example>
    Example Input:

    Text:
    Text: "the latest report on the fiscal year 2024, including revenue growth,
           operating margins, and projections for Q4."
    Example Output: FY2024-Revenue-Growth-Q4-Projections
    </Example>

    Text:
    "{text}"
    """
    name: str = client.get_completion(prompt, model=model_name, 
                                      temperature=temperature, max_tokens=max_tokens)
    return name + ext


def try_test_prompt(client: Client) -> str:
    prompt: str = "Do not return anything."
    return client.get_completion(prompt)


def generate_topic(
    client: Client, 
    text: str, 
    model_name: str = "claude-3-5-haiku-latest",
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """
    Generate a topic as a summary of the given text.

    Args:
        client: Client
        text: str
        model_name: str = "claude-3-5-sonnet-latest"
        temperature: float = 0.3
        max_tokens: int = 4096

    Returns:
        A topic as a summary of the given text.
    """
    prompt: str = f"""
        Extract the single most important topic from the text below, using 1-5 words in a clear, concise phrase. 
        If the text lacks any substantive topic or meaningful content, output exactly 'Generic Topic':
        
        <Text>
        {text}
        </Text>

        <Example>
        Example with topic: "The rapid advancement of artificial intelligence has led to breakthroughs in healthcare diagnostics."
        Output: AI healthcare diagnostics
        
        Example without topic: "Things happened and stuff occurred in places with people."
        Output: Generic Topic
        </Example>
    """
    return client.get_completion(prompt, model=model_name, 
                                 temperature=temperature, max_tokens=max_tokens)
