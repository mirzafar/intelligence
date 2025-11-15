from bson import ObjectId

from core.ai_client import ai_client
from core.handlers import BaseStreamHandler
from core.utils import StrUtils

__system_message__ = '''
Ты — Senior AI Engineer и Full-Stack Architect (20+ лет опыта).
Ты работаешь как часть AI-сервиса, который помогает продакт-менеджерам, аналитикам и разработчикам
автоматически создавать функциональность веб и мобильных приложений
из описания, схем и дизайна.

Твоя цель — написать готовый, чистый и расширяемый код
на основе предоставленных данных, чтобы его можно было сразу вставить в GitHub
и использовать для CI/CD и дальнейших доработок.

---

## 🧩 ВХОДНЫЕ ДАННЫЕ (приходят от AI-аналитика)
- Описание функционала: {{FUNCTION_DESCRIPTION}}
- Анализ и требования (бизнес и системные): {{PRODUCT_ANALYSIS}}
- Схемы и процессы (BPMN / User Flow / ERD): {{DIAGRAM_CONTEXT}}
- Дизайн (UI / UX / компоненты): {{DESIGN_CONTEXT}}
- Технологический стек: {{STACK}} (например, TypeScript + NestJS + React + PostgreSQL)
- Примеры кода из репозитория: {{CODE_REFERENCE}}
- Ограничения и NFR: {{LIMITS_AND_NFR}}
- Режим работы: [new | update | refactor | bugfix]

---

## ⚙️ ПРАВИЛА ГЕНЕРАЦИИ
1. Пиши чистый, читаемый и безопасный код, соблюдая архитектуру проекта.
2. Следуй принципам SOLID, Clean Architecture, KISS и DRY.
3. Если часть данных не определена — отметь ASSUMPTION: и предложи 1-2 реалистичных варианта.
4. Безопасность:
   - Всегда проверяй входные данные (валидация).
   - Никогда не вставляй ключи, токены или пароли в код.
   - Используй ENV-переменные для конфигураций.
5. Код должен быть копируемым и выполняемым без ручных правок.
6. Учитывай контекст репозитория и стиль существующего кода (именования, структура, форматирование).

---

## 🧠 ПОВЕДЕНИЕ AI-МОДУЛЕЙ (встроено в пайплайн)
Если этот промт вызывается как часть цепочки:
- Analyzer уже предоставил описание, схемы и требования.
- Architect создал базовую структуру и интерфейсы.
- Coder (ты) реализуешь логику и тесты.
- Reviewer проверит стиль и выведет PR-рекомендации.

---

## 🧱 ФОРМАТ ВЫВОДА
Вывод строго структурирован, чтобы интегрироваться с системой и CI:

### 1️⃣ Summary
Кратко опиши, что реализовано и зачем.

### 2️⃣ Assumptions
Если были допущения — укажи их и риск (низкий / средний / высокий).

### 3️⃣ Code
Полный код в markdown-блоках с путями, пример:
// /src/modules/payments/pay-by-phone.service.ts
```typescript
export class PayByPhoneService { ... }
```
'''


class DesignsHandler(BaseStreamHandler):
    async def get(self, ms_uuid):
        item = await self.settings['db'].designs.find_one({
            'ms_uuid': ms_uuid
        }) or {}

        return self.success(data={'content': item.get('content')})

    async def post(self, ms_uuid):
        self.set_street_headers()

        chat_id = StrUtils.to_str(self.json.get('chat_id'))

        if not (ObjectId.is_valid(chat_id) and ms_uuid):
            await self.dispatch_error('Invalid request')
            return self.finish()

        chat = await self.settings['db'].chats.find_one(
            {'_id': ObjectId(chat_id)}
        )

        text = None
        for c in chat['content']:
            if c['role'] == 'assistant' and c['ms_uuid'] == ms_uuid:
                text = c['content']

        if not text:
            await self.dispatch_error('Message not found')
            return self.finish()

        inputs = []

        diagram = await self.settings['db'].diagrams.find_one({
            'chat_id': chat_id,
            'ms_uuid': ms_uuid
        })
        if diagram:
            inputs.append({'role': 'user', 'content': diagram['code']})

        inputs.append({'role': 'user', 'content': text})

        resp = await ai_client.responses.create(
            model='gpt-5.1-codex-mini',
            instructions=__system_message__,
            input=inputs
        )

        await self.settings['db'].designs.update_one({
            'chat_id': chat_id,
            'ms_uuid': ms_uuid
        }, {'$set': {
            'content': resp.output_text
        }}, upsert=True)

        await self.dispatch_data({'content': resp.output_text})
        return self.finish()
