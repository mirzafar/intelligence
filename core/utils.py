import os
import uuid
from typing import Optional

import aiofiles
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph

from settings import settings


class StrUtils:
    @staticmethod
    def to_str(value):
        return str(value) if value is not None else ''


class ListUtils:
    @staticmethod
    def to_list_of_strs(value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]


pdfmetrics.registerFont(TTFont("Arial", f"{settings['root_dir']}/static/ARIAL.TTF"))

arial_style = ParagraphStyle(
    name="ArialStyle",
    fontName="Arial",
    fontSize=12,
    leading=16,
    firstLineIndent=0,
    leftIndent=0,
    rightIndent=0,
    spaceAfter=8,
)

styles = getSampleStyleSheet()


async def save_file(file, _type: str = 'text') -> tuple[bool, Optional[str]]:
    if not file:
        return False, None

    file_path = settings.get('root_dir', '') + '/static/uploads'
    uid = str(uuid.uuid4())

    if _type == 'text':
        file_name = f'{file_path}/{uid[:2]}/{uid[2:4]}/{uid}.pdf'
        os.makedirs(f'{file_path}/{uid[:2]}/{uid[2:4]}', 0o755, True)

        pdf = SimpleDocTemplate(file_name, pagesize=A4)
        story = []

        for x in file.splitlines():
            story.append(Paragraph(x, arial_style))

        pdf.build(story)

        return True, f'{uid[:2]}/{uid[2:4]}/{uid}.pdf'

    else:
        ext = file.name.split('.')[len(file.name.split('.')) - 1]
        file_name = f'{file_path}/{uid[:2]}/{uid[2:4]}/{uid}.{ext}'
        os.makedirs(f'{file_path}/{uid[:2]}/{uid[2:4]}', 0o755, True)

        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(file.body)

        return True, f'{uid[:2]}/{uid[2:4]}/{uid}.{ext}'
