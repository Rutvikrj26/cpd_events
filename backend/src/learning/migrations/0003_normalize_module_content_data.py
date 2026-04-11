"""
Rewrite legacy ModuleContent.content_data shapes to the canonical schema.

- content_type='text': ensure {"body": str}, converting from {"text": str}
  or {"text": {"body": str}}.
- content_type='lesson': ensure lesson.text is {"body": str} (wrap plain
  strings) and lesson.video is {"url": str} (wrap plain strings).
- Other content types are left alone.
"""

from django.db import migrations


def _normalize(content_type, content_data):
    if not isinstance(content_data, dict):
        return content_data or {}
    data = dict(content_data)
    if content_type == 'text':
        if 'body' not in data:
            legacy = data.pop('text', None)
            if isinstance(legacy, str):
                data['body'] = legacy
            elif isinstance(legacy, dict) and isinstance(legacy.get('body'), str):
                data['body'] = legacy['body']
    elif content_type == 'lesson':
        text_block = data.get('text')
        if isinstance(text_block, str):
            data['text'] = {'body': text_block}
        video_block = data.get('video')
        if isinstance(video_block, str):
            data['video'] = {'url': video_block}
    return data


def forwards(apps, schema_editor):
    ModuleContent = apps.get_model('learning', 'ModuleContent')
    updated = 0
    for row in ModuleContent.objects.all().iterator():
        normalized = _normalize(row.content_type, row.content_data)
        if normalized != row.content_data:
            row.content_data = normalized
            row.save(update_fields=['content_data', 'updated_at'])
            updated += 1
    if updated:
        print(f"normalized {updated} ModuleContent rows")


def backwards(apps, schema_editor):
    # Legacy shapes are permissive supersets, so reverting is a no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_coursestaff'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
