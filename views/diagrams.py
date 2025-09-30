import json

from bson import ObjectId

from core.ai_client import ai_client
from core.handlers import BaseHandler
from core.utils import StrUtils


class DiagramsHandler(BaseHandler):
    async def get(self):
        filters = {
            'is_saved': True
        }

        items = await self.settings['db'].diagrams.find(filters).sort('_id', -1).to_list(length=None)

        self.success(data={'items': [
            {
                'title': i['title'],
                'ms_uuid': i['ms_uuid']
            } for i in items
        ]})

    async def post(self):
        data = json.loads(self.request.body or '{}')

        title = StrUtils.to_str(data.get('title'))
        ms_uuid = StrUtils.to_str(data.get('ms_uuid'))

        if not (ms_uuid or title):
            return self.error('Invalid request')

        await self.settings['db'].diagrams.update_one({'ms_uuid': ms_uuid}, {'$set': {
            'title': title,
            'is_saved': True
        }})

        return self.success()


class DiagramHandler(BaseHandler):
    async def get(self, ms_uuid):
        item = await self.settings['db'].diagrams.find_one({
            'ms_uuid': ms_uuid
        }) or {}

        return self.success(data={'code': item.get('code')})

    async def post(self, ms_uuid):
        data = json.loads(self.request.body or '{}')

        chat_id = StrUtils.to_str(data.get('chat_id'))

        if not (ObjectId.is_valid(chat_id) and ms_uuid):
            return self.error('Invalid request')

        diagram = await self.settings['db'].diagrams.find_one(
            {'ms_uuid': ms_uuid}
        )

        if diagram:
            return self.success()

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
                           'No explanations, no markdown, no backticks. Use double quotes " around all node labels'
            },
            {'role': 'user', 'content': text}
        ]

        resp = await ai_client.responses.create(
            model='gpt-4o-mini',
            input=content
        )

        content.append({'role': 'assistant', 'content': resp.output_text})

        await self.settings['db'].diagrams.insert_one({
            'chat_id': chat_id,
            'ms_uuid': ms_uuid,
            'content': content,
            'code': resp.output_text
        })

        return self.success()

    async def put(self, ms_uuid):
        if not ms_uuid:
            return self.error('Invalid request')

        data = json.loads(self.request.body or '{}')

        action = StrUtils.to_str(data.get('action'))
        if action == 'edit-code':
            code = StrUtils.to_str(data.get('code'))

            if not code:
                return self.error('Invalid request')

            diagram = await self.settings['db'].diagrams.find_one(
                {'ms_uuid': ms_uuid}
            )

            if not diagram:
                return self.error(message='Diagram not found')

            contents = list(reversed(diagram['content']))
            for c in contents:
                if c['role'] == 'assistant':
                    c['content'] = code
                    break

            await self.settings['db'].diagrams.update_one({'ms_uuid': ms_uuid}, {'$set': {
                'content': list(reversed(contents)),
                'code': code
            }})

        elif action == 're-generate':
            prompt = StrUtils.to_str(data.get('prompt'))

            if not prompt:
                return self.error('Invalid request')

            diagram = await self.settings['db'].diagrams.find_one(
                {'ms_uuid': ms_uuid}
            )

            if not diagram:
                return self.error(message='Diagram not found')

            content = diagram['content']
            content.append({'role': 'user', 'content': prompt})

            resp = await ai_client.responses.create(
                model='gpt-4o-mini',
                input=content
            )

            content.append({'role': 'assistant', 'content': resp.output_text})

            await self.settings['db'].diagrams.update_one({'ms_uuid': ms_uuid}, {'$set': {
                'content': content,
                'code': resp.output_text
            }})

            return self.success(data={})

        return self.error('Unknown action')
