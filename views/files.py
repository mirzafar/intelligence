import traceback
from datetime import datetime
from urllib.parse import quote

from bson import ObjectId
from pymongo import ReturnDocument

from core.ai_client import ai_client
from core.handlers import BaseHandler
from core.utils import save_file
from settings import settings


class FilesHandler(BaseHandler):
    async def get(self):
        items = await self.settings['db'].files.find({
            'is_active': True
        }).sort('_id', -1).to_list(length=None)

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
            if ai_client.vector_store_id:
                await ai_client.vector_stores.file_batches.create_and_poll(
                    vector_store_id=ai_client.vector_store_id,
                    file_ids=[upload_file.id]
                )
                await ai_client.calc_files()

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

        return self.success(data={'items': data})


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
                if ai_client.vector_store_id:
                    try:
                        await ai_client.vector_stores.files.delete(
                            vector_store_id=ai_client.vector_store_id,
                            file_id=file['external_id']
                        )
                        await ai_client.calc_files()
                    except (Exception,):
                        traceback.print_exc()
            except (Exception,):
                traceback.print_exc()

        return self.success(data={})


class FileDownloadHandler(BaseHandler):
    async def get(self, file_id):
        item = await self.settings['db'].files.find_one({
            '_id': ObjectId(file_id)
        })
        if not item or not item.get('file_path'):
            return self.error(message='File not found')

        file_path = settings['root_dir'] + '/static/uploads/' + item['file_path']

        download_filename = f"{item['title']}"

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', f'attachment; filename="{quote(download_filename)}"')

        with open(file_path, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                self.write(data)

        return self.finish()
