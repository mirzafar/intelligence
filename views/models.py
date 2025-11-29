from bson import ObjectId

from core.handlers import BaseHandler
from core.utils import StrUtils


class ModelsHandler(BaseHandler):
    async def get(self):
        items = await self.settings['db'].models.find({
            'is_active': True
        }).sort('_id', -1).to_list(length=None)

        return self.success(data={'items': items})

    async def post(self):
        title = StrUtils.to_str(self.json.get('title'))
        if not title:
            return self.error('Не передан "Название"')

        prompt = StrUtils.to_str(self.json.get('prompt'))
        if not prompt:
            return self.error('Не передан "Системный промпт"')

        await self.settings['db'].models.insert_one({
            'title': title,
            'prompt': prompt,
            'use_knowledge_base': bool(self.json.get('use_knowledge_base')),
            'is_active': True
        })
        return self.success()


class ModelHandler(BaseHandler):
    async def get(self, model_id):
        item = await self.settings['db'].models.find_one({
            '_id': ObjectId(model_id)
        })
        return self.success(data={'item': item})

    async def put(self, model_id):
        if not (ObjectId.is_valid(model_id) and model_id):
            return self.error('Invalid request')

        title = StrUtils.to_str(self.json.get('title'))
        if not title:
            return self.error('Не передан "Название"')

        prompt = StrUtils.to_str(self.json.get('prompt'))
        if not prompt:
            return self.error('Не передан "Системный промпт"')

        await self.settings['db'].models.update_one({'_id': ObjectId(model_id)}, {'$set': {
            'title': title,
            'prompt': prompt,
            'use_knowledge_base': bool(self.json.get('use_knowledge_base')),
        }})
        return self.success()

    async def delete(self, model_id):
        if not (ObjectId.is_valid(model_id) and model_id):
            return self.error('Invalid request')

        await self.settings['db'].models.delete_one({'_id': ObjectId(model_id)})
        return self.success()
