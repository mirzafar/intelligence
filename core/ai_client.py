from typing import Union

import openai
from openai import AsyncOpenAI

from settings import settings


class AiClient:
    client = None
    vector_store_name: str = settings['environment']
    vector_store_id: str = None
    has_files: bool = False

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings['ai_api_key']
        )

    def __getattr__(self, attr):
        if self.client is None:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        return getattr(self.client, attr)

    async def initialize_vector_store(self):
        if self.vector_store_id:
            files = await self.client.vector_stores.files.list(vector_store_id=self.vector_store_id)
            if len(files.data or []) > 0:
                self.has_files = True
            print(
                f'AiClient#initialize_vector_store() -> '
                f'vector_store_id: {self.vector_store_id}, has_files: {self.has_files}'
            )
            return

        vectors = await self.client.vector_stores.list()
        for vector in (vectors.data or []):
            if vector.name == self.vector_store_name:
                self.vector_store_id = vector.id
                if vector.file_counts.completed > 0:
                    self.has_files = True
                print(
                    f'AiClient#initialize_vector_store() -> '
                    f'vector_store_id: {self.vector_store_id}, has_files: {self.has_files}'
                )
                return

        vector = await self.client.vector_stores.create(name=self.vector_store_name, expires_after={
            'anchor': 'last_active_at',
            'days': 30
        })
        self.vector_store_id = vector.id
        print(f'AiClient#initialize_vector_store() -> vector_store_id: {self.vector_store_id}')
        return

    @property
    def get_store_id(self):
        return self.vector_store_id

    async def calc_files(self):
        if self.vector_store_id:
            files = list(await self.client.vector_stores.files.list(vector_store_id=self.vector_store_id))
            if files:
                self.has_files = True


ai_client = AiClient()  # type: Union[openai.AsyncOpenAI, AiClient]
