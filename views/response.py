import json
import traceback
from datetime import datetime
from typing import List
from uuid import uuid4

import tornado.websocket
import ujson
from bson import ObjectId
from pymongo import ReturnDocument

from core.ai_client import ai_client
from core.utils import StrUtils, system_message


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
        if not chat:
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
                inserted = await self.settings['db'].chats.insert_one(data)
                if inserted.inserted_id:
                    chat_id = str(inserted.inserted_id)

            self.write(ujson.dumps({'text': text, 'chat_id': chat_id}))

        else:
            self.write('ERROR')

        await self.flush()
