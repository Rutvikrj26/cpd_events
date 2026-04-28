"""Trigram-backed GIN index on TranscriptSegment.text for the search endpoint.

Postgres-only. The runtime is conditional on `connection.vendor` so SQLite
test runs (which the conferencing test suite uses for speed) skip cleanly
without raising. The downside is that test-time search behaviour can't
exercise the GIN path — search-endpoint integration tests must run against
a Postgres fixture.

Why trigram instead of the standard `to_tsvector` full-text:
  - Trigram tolerates partial words ("emerg" matches "emergency"), which
    is the likely user behaviour in a transcript search box.
  - English-only stemming is a poor fit for medical terminology where
    learners often search for prefixes ("muco-", "broncho-").
  - The cost is index size (~2-3x text size) and write amplification on
    edits — acceptable tradeoffs because transcripts are read-heavy after
    finalization.
"""

from django.db import connection, migrations


def create_trgm_index(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cur:
        cur.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
        cur.execute(
            'CREATE INDEX IF NOT EXISTS transcript_segments_text_trgm_idx '
            'ON transcript_segments USING gin (text gin_trgm_ops)'
        )


def drop_trgm_index(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cur:
        cur.execute('DROP INDEX IF EXISTS transcript_segments_text_trgm_idx')


class Migration(migrations.Migration):
    dependencies = [
        ('conferencing', '0003_transcript_transcriptsegment'),
    ]

    operations = [
        migrations.RunPython(create_trgm_index, drop_trgm_index),
    ]
