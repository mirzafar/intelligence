import os
import traceback
from datetime import datetime
from urllib.parse import quote
from uuid import uuid4

from bson import ObjectId
from pymongo import ReturnDocument

from core.ai_client import ai_client
from core.handlers import BaseHandler
from core.utils import save_file
from settings import settings


class DiagramsHandler(BaseHandler):
    async def get(self):
        filters = {
            'is_active': True
        }

        items = await self.settings['db'].diagrams.find(filters).sort('_id', -1).to_list(length=None)

        # self.success(data={'items': items})
        self.success(data={'items': [
            {'_id': ObjectId(), 'title': 'test'}
        ]})

    async def post(self):
        # data = {
        #     'title': file.filename,
        #     'is_active': True,
        #     'external_id': upload_file.id,
        #     'file_path': file_path,
        #     'created_at': datetime.now()
        # }
        #
        # inserted = await self.settings['db'].files.insert_one(data)
        #
        # if not inserted.inserted_id:
        #     return self.error(message='Операция не выполнена')

        # self.success(data={'items': data})
        self.success(data={})


class DiagramHandler(BaseHandler):
    async def get(self, chat_id, ms_uuid):
        item = await self.settings['db'].diagrams.find_one({
            'ms_uuid': ms_uuid
        }) or {}

        self.success(data={'code': item.get('code')})

    async def post(self, chat_id, ms_uuid):
        if not (ObjectId.is_valid(chat_id) and ms_uuid):
            return self.error('Invalid request')

        diagram = await self.settings['db'].diagrams.find_one(
            {'ms_uuid': ms_uuid}
        )

        if diagram:
            return self.success(data={})

        chat = await self.settings['db'].chats.find_one(
            {'_id': ObjectId(chat_id)}
        )

        if not chat:
            return self.error('Chat not found')

        text = None
        for c in chat['content']:
            if c['role'] == 'assistant' and c['ms_uuid'] == ms_uuid:
                text = c['content']

        if not text:
            return self.error('Message not found')

        content = [
            {
                'role': 'system',
                'content': 'You are an assistant that outputs ONLY raw flowchart code in Mermaid format. '
                           'No explanations, no markdown, no backticks.'
            },
            {'role': 'user', 'content': text}
        ]

        resp = await ai_client.responses.create(
            model='gpt-4o-mini',
            input=content
        )

        content.append({'role': 'assistant', 'content': resp.output_text})

        await self.settings['db'].diagrams.insert_one({
            'ms_uuid': ms_uuid,
            'content': content,
            'code': resp.output_text
        })

        return self.success(data={})
