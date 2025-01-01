import requests
import json
import re

from tqdm import tqdm
import yfinance as yf

from minerva.llm.chunk import chunk_and_parse_output
from minerva.llm.client import AnthropicClient
from minerva.llm.useful import generate_topic
from minerva.util.env import ANTHROPIC_API_KEY


client: AnthropicClient = AnthropicClient(ANTHROPIC_API_KEY)


def _get_num_sentences(text: str) -> int:
    """Count the number of sentences in the given text."""
    return len(re.split(r'[.!?]', text)) - 1


def _chunk(transcripts: list[dict] | str, min_sentences: int = 7) -> list[dict[str, int | str]]:
    """
    Chunk the given list of texts into smaller chunks.

    Args:
        transcripts: The list of transcripts to chunk.
        min_sentences: The minimum number of sentences in a chunk. If a text has fewer
            than this number of sentences, it will be added to the output as a single chunk.

    Returns:
        A list of chunks information in the format of
        ```python
        [
            {
                "speaker_index": int,
                "chunk_index": int,
                "chunk_topic": str,
                "text": str
            }
        ]
        ```
    """
    if isinstance(transcripts, dict):
        transcripts = [transcripts]

    chunks: list[dict] = []
    chunk_index: int = 0
    for transcript_map in transcripts:
        transcript_index: int = transcript_map["index"]
        text: str = transcript_map["text"]
        num_sentences: int = _get_num_sentences(text)
        if num_sentences < min_sentences:
            chunks.append({
                "transcript_index": transcript_index,
                "chunk_index": chunk_index,
                "chunk_topic": generate_topic(client, text),
                "chunk": text
            })
            chunk_index += 1
            continue

        chunks_i: list[dict] = chunk_and_parse_output(text)
        if not chunks_i:
            print(f"`_chunk`: Error/empty chunking text: {text}")
            continue

        for chunk_i in chunks_i:
            chunk_i["transcript_index"] = transcript_index
        chunk_index += len(chunks_i)
        chunks.extend(chunks_i)

    return chunks


def get_company_info(ticker: str) -> dict | None:
    try:
        return yf.Ticker(ticker).info
    except yf.exceptions.YFException as e:
        print(f"`get_company_info`: Error fetching company info for {ticker}: {e}")
        return None


def parse_transcript(transcript: str) -> list[dict[str, int | str]]:
    """
    Parse the transcript dictionary into the format of
    ```python
    [
        {
            "speaker_index": int,
            "speaker": str,
            "text": str
        }
    ]
    ```
    """
    # Regular expression to capture the speaker and their text
    speaker_regex = re.compile(
        r"([A-Za-z\s]+):\s*(.*?)(?=(?:\n[A-Za-z\s]+:|$))", re.DOTALL)

    # Find all matches
    matches = speaker_regex.findall(transcript)
    
    # Add them to the parsed list in the desired format
    parsed: list[dict[str, str| int]] = []
    for i, match in enumerate(matches):
        speaker: str = match[0].strip()
        text: str = match[1].strip()
        parsed.append({"speaker_index": i, "speaker": speaker, "text": text})
        print(f"[{i}] {speaker}: {text}", end="\n\n")

    return parsed

    # parsed_lst: list[dict[str, str]] = []
    # for i, line in enumerate(transcript.split("\n")):
    #     line_split: list[str] = line.split(":")
    #     speaker: str = line_split[0]
    #     text: str = ":".join(line_split[1:])
    #     parsed_lst.append({"index": i, "speaker": speaker, "text": text})
    # return parsed_lst


def get_one_transcript(ticker: str, year: int, quarter: int) -> dict[str, int | str] | None:
    """
    Get the transcript for a given ticker, year, and quarter, in the format of
    ```python
    {
        "year": int,
        "quarter": int,
        "transcript": [
            {
                "index": int,
                "speaker": str,
                "text": str
            }
        ]
    }
    ```
    """
    api_url: str = ("https://api.api-ninjas.com/v1/earningstranscript?"
                    f"ticker={ticker}&year={year}&quarter={quarter}")
    response = requests.get(api_url, headers={'X-Api-Key': 'YOUR_API_KEY'})
    if response.status_code == requests.codes.ok:
        transcript_info: list | dict = json.loads(response.text)
        if not transcript_info or "transcript" not in transcript_info: # empty list
            return None
        return {
            "year": year,
            "quarter": quarter,
            "transcript": parse_transcript(transcript_info["transcript"])
        }
    else:
        print("Error:", response.status_code, response.text)
        return None


def get_transcripts(
    ticker: str, 
    start_year: int, 
    end_year: int,
    start_quarter: int,
    end_quarter: int,
    chunk_transcripts: bool = False
) -> list[dict[str, int | str]]:
    """
    Get the transcripts for a given ticker, start year, and end year, in the format of
    ```python
    [
        {
            "year": int,
            "quarter": int,
            "transcript": [
                {
                    "index": int,
                    "speaker": str,
                    "text": str
                }
            ]
        }
    ]
    ```

    Args:
        ticker: The ticker of the company.
        start_year: The start year to get transcripts.
        end_year: The end year to get transcripts.
        start_quarter: The start quarter to get transcripts.
        end_quarter: The end quarter to get transcripts.
        chunk_transcripts: Whether to chunk the transcripts into smaller chunks.
    """
    transcripts: list[dict[str, int | str]] = []
    for year in tqdm(range(start_year, end_year + 1), desc="Years"):
        for quarter in tqdm(range(start_quarter, end_quarter + 1), desc="Quarters"):
            try:
                transcript_map: dict[str, int | str] | None = get_one_transcript(ticker, year, quarter)
                if not transcript_map:
                    continue

                if chunk_transcripts:
                    transcript_map["chunking_output"] = _chunk(transcript_map["transcript"])
                transcripts.append(transcript_map)

            except Exception as e:
                print(f"get_transcripts: Error fetching transcript for {ticker} "
                      f"{year}-Q{quarter}: {e}")
                raise

    return transcripts


def construct_company_kb(
    ticker: str, 
    start_year: int, 
    end_year: int,
    start_quarter: int,
    end_quarter: int,
    chunk_transcripts: bool = False
) -> dict[str, list | str]:
    """
    Get the transcript for a given ticker, year, and quarter, in the format of
    ```python
    {
        "ticker": str,
        "company_name": str,
        "sector": str,
        "industry": str,
        "transcripts": [
            {
                "year": int,
                "quarter": int,
                "transcript": [
                    {
                        "index": int,
                        "speaker": str,
                        "text": str
                    }
                ]
            }
        ]
    }
    ```

    Args:
        ticker: The ticker of the company.
        start_year: The start year to get transcripts.
        end_year: The end year to get transcripts.
        start_quarter: The start quarter to get transcripts.
        end_quarter: The end quarter to get transcripts.
        chunk_transcripts: Whether to chunk the transcripts into smaller chunks.
    """
    company_info: dict[str, str] | None = get_company_info(ticker)
    out = {
        "ticker": ticker,
        "transcripts": get_transcripts(ticker, start_year, end_year, 
                                       start_quarter, end_quarter, chunk_transcripts)
    }
    if company_info:
        out["company_name"] = company_info.get("longName", "")
        out["sector"] = company_info.get("sector", "")
        out["industry"] = company_info.get("industry", "")
    return out
