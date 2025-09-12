import json
import os
import traceback
from datetime import datetime
from typing import List
from urllib.parse import quote
from uuid import uuid4

import tornado.websocket
from bson import ObjectId
from pymongo import ReturnDocument

from core.ai_client import ai_client
from core.handlers import BaseHandler
from core.utils import StrUtils, system_message, save_file
from settings import settings


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("resr.html")


class ResponseHandler(tornado.web.RequestHandler):
    @classmethod
    async def function(
        cls, prompt: str, ms_uuid: str, file_ids: list = None, content: List[dict] = None
    ) -> tuple[bool, str, list]:
        try:
            if not content:
                content = [
                    {'role': 'system', 'content': system_message},
                ]

            for file_id in file_ids or []:
                content.append({
                    'role': 'user',
                    'content': [{
                        'type': 'input_file',
                        'file_id': file_id
                    }]
                })

            content.append({
                'role': 'user',
                'content': [
                    {'type': 'input_text', 'text': prompt}
                ]
            })

            input_content = []
            for c in content:
                if c['role'] in ['assistant']:
                    input_content.append({
                        'role': 'assistant',
                        'content': c['content']
                    })
                else:
                    input_content.append(c)

            response = await ai_client.responses.create(
                model='gpt-5-nano',
                input=input_content
            )

            if response.output_text:
                response_txt = response.output_text
            else:
                return False, 'ERROR', content

            content.append({
                'role': 'assistant',
                'content': response_txt,
                'ms_uuid': ms_uuid
            })

            return True, response_txt, content

        except (Exception,) as er:
            traceback.print_exc()
            return False, 'ERROR', content

    async def post(self):
        self.set_header('Content-Type', 'text/plain')
        data = json.loads(self.request.body)

        prompt = StrUtils.to_str(data.get('prompt'))
        chat_id = StrUtils.to_str(data.get('chat_id'))
        ms_uuid = StrUtils.to_str(data.get('ms_uuid')) or uuid4()

        if self.request.connection.stream.closed():
            return

        chat = None
        if chat_id:
            chat = await self.settings['db'].chats.find_one({
                '_id': ObjectId(chat_id)
            })

        file_ids = None
        if chat:
            file_ids = await self.settings['db'].files.distinct('external_id', {'is_active': True})

        success, text, content = await self.function(
            prompt=prompt,
            file_ids=file_ids,
            content=chat['content'] if chat else None,
            ms_uuid=ms_uuid
        )

        if success:
            data = {
                'is_active': True,
                'content': content,
                'updated_at' if chat else 'created_at': datetime.now()
            }

            if chat:
                await self.settings['db'].chats.update_one({'_id': ObjectId(chat_id)}, {'$set': data})
            else:
                await self.settings['db'].chats.insert_one(data)

            self.write(text)

        else:
            self.write('ERROR')

        await self.flush()


class ChatsHandler(BaseHandler):
    async def get(self):
        filters = {
            'is_active': True,
        }

        items = await self.settings['db'].chats.find(filters).sort('_id', -1).to_list(length=None)
        data = []
        for item in items:
            if not item.get('content'):
                continue

            title = None
            for c in item['content']:
                if c['role'] in ['user']:
                    title = c['content'][0]['text']
                    break

            data.append({
                '_id': str(item['_id']),
                'title': title
            })

        self.success(data={'items': data})


class ChatHandler(BaseHandler):
    async def get(self, chat_id):
        item = await self.settings['db'].chats.find_one({
            '_id': ObjectId(chat_id)
        })

        content = []
        if item and item.get('content'):
            for c in item['content']:
                if c['role'] in ['system']:
                    continue

                elif c['role'] == 'user':
                    if c['content'][0]['type'] == 'input_file':
                        continue

                    content.append({
                        'role': 'user',
                        'text': c['content'][0]['text']
                    })

                elif c['role'] == 'assistant':
                    content.append({
                        'role': 'assistant',
                        'text': c['content'],
                        'ms_uuid': c.get('ms_uuid')
                    })

        self.success(data={'content': content})

    async def delete(self, chat_id):
        await self.settings['db'].chats.update_one({
            '_id': ObjectId(chat_id)
        }, {'$set': {'is_active': False}})

        self.success(data={})

    async def put(self, chat_id):
        data = json.loads(self.request.body)
        action = StrUtils.to_str(data.get('action'))
        if action == 'redirect':
            filename = StrUtils.to_str(data.get('filename'))
            text = StrUtils.to_str(data.get('text'))
            if not (text or filename):
                return self.error('Not found text')

            success, file_path = await save_file(text)
            if not success:
                return self.error('Error saving file')

            try:
                upload_file = await ai_client.files.create(
                    file=(filename, text),
                    purpose='assistants'
                )
            except (Exception,) as er:

                return self.error(message=str(er))

            data = {
                'title': filename,
                'is_active': True,
                'external_id': upload_file.id,
                'file_path': file_path,
                'created_at': datetime.now()
            }

            inserted = await self.settings['db'].files.insert_one(data)

            if not inserted.inserted_id:
                return self.error(message='Операция не выполнена')

            return self.success(data={})

        return self.error('Unknown action')


class FilesHandler(BaseHandler):
    async def get(self):
        filters = {
            'is_active': True
        }

        items = await self.settings['db'].files.find(filters).sort('_id', -1).to_list(length=None)

        self.success(data={'items': items})

    async def post(self):
        files = self.request.files['files']
        if not files:
            return self.error(message='Отсуствует обязательный параметры "Файл"')

        file = files[0]
        if not file:
            return self.error(message='Отсуствует обязательный параметры "Файл"')

        count = await self.settings['db'].files.count_documents({'is_active': True}) or 0
        if count > 20:
            return self.error(message='Файл больше лимита. Лимит: 20')

        success, file_path = await save_file(file, 'file')
        if not success:
            return self.error(message='Error saving file')

        try:
            upload_file = await ai_client.files.create(
                file=(file.filename, file.body),
                purpose='assistants'
            )
        except (Exception,) as er:

            return self.error(message=str(er))

        data = {
            'title': file.filename,
            'is_active': True,
            'external_id': upload_file.id,
            'file_path': file_path,
            'created_at': datetime.now()
        }

        inserted = await self.settings['db'].files.insert_one(data)

        if not inserted.inserted_id:
            return self.error(message='Операция не выполнена')

        self.success(data={'items': data})


class FileHandler(BaseHandler):
    async def get(self, file_id):
        item = await self.settings['db'].files.find_one({
            '_id': ObjectId(file_id)
        })

        self.success(data={'item': item})

    async def delete(self, file_id):
        file = await self.settings['db'].files.find_one_and_update({
            '_id': ObjectId(file_id)
        }, {'$set': {'is_active': False}}, return_document=ReturnDocument.AFTER)

        if file.get('external_id'):
            try:
                await ai_client.files.delete(file['external_id'])
            except (Exception,):
                traceback.print_exc()

        self.success(data={})


class FileDownloadHandler(BaseHandler):
    async def get(self, file_id):
        item = await self.settings['db'].files.find_one({
            '_id': ObjectId(file_id)
        })
        if not item or not item.get('file_path'):
            return self.error(message='File not found')

        file_path = settings.get('root_dir', '') + '/static/uploads/' + item['file_path']

        original_filename = os.path.basename(item['file_path'])
        file_extension = os.path.splitext(original_filename)[1]
        download_filename = f"{item['title']}{file_extension}"

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', f'attachment; filename="{quote(download_filename)}"')

        with open(file_path, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                self.write(data)

        self.finish()
