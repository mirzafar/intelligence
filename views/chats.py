import json
from datetime import datetime

from bson import ObjectId

from core.ai_client import ai_client
from core.handlers import BaseHandler
from core.utils import StrUtils, save_file
from settings import settings


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
                    if c['content'][0]['type'] == 'input_file':
                        continue

                    title = c['content'][0]['text']
                    break

            data.append({
                '_id': str(item['_id']),
                'title': title
            })

        return self.success(data={'items': data})


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
                    file=open(settings.get('root_dir', '') + '/static/uploads/' + file_path, 'rb'),
                    purpose='assistants'
                )
            except (Exception,) as er:

                return self.error(message=str(er))

            item = {
                'title': filename,
                'is_active': True,
                'external_id': upload_file.id,
                'file_path': file_path,
                'created_at': datetime.now()
            }

            inserted = await self.settings['db'].files.insert_one(item)

            if not inserted.inserted_id:
                return self.error(message='Операция не выполнена')

            return self.success(data={})

        elif action == 'edit_message':
            chat = await self.settings['db'].chats.find_one(
                {'_id': ObjectId(chat_id)}
            )

            if not chat:
                return self.error('Chat not found')

            content = chat['content']
            for c in content:
                if c['role'] == 'assistant' and data.get('text') and c['ms_uuid'] == data.get('messageId'):
                    c['content'] = data.get('text')

            await self.settings['db'].chats.update_one({'_id': ObjectId(chat_id)}, {'$set': {'content': content}})

            return self.success(data={})

        return self.error('Unknown action')
