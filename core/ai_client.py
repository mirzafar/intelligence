from typing import Union

import openai
from openai import AsyncOpenAI

from settings import settings


class AiClient:
    client = None

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings['ai_api_key']
        )

    def __getattr__(self, attr):
        if self.client is None:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        return getattr(self.client, attr)


ai_client = AiClient()  # type: Union[openai.AsyncOpenAI, AiClient]
