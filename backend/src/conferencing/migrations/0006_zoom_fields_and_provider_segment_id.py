"""Zoom migration prep:

* VideoRoom: add zoom_meeting_id + zoom_join_url (nullable; legacy LiveKit
  rows unaffected).
* TranscriptSegment: rename livekit_segment_id → provider_segment_id and
  rename the unique constraint to match. RenameField + RenameConstraint
  preserve existing data and indexes; we replace the named index too so
  Postgres doesn't keep a stale index name pointing at a renamed column.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conferencing', '0005_videoroom_one_active_room_per_content'),
    ]

    operations = [
        # ---- VideoRoom: Zoom fields ----
        migrations.AddField(
            model_name='videoroom',
            name='zoom_meeting_id',
            field=models.CharField(blank=True, db_index=True, help_text='Zoom numeric meeting ID', max_length=32),
        ),
        migrations.AddField(
            model_name='videoroom',
            name='zoom_join_url',
            field=models.URLField(blank=True, help_text='Generic Zoom join URL for this meeting', max_length=1000),
        ),

        # ---- TranscriptSegment: rename livekit_segment_id ----
        # The old unique constraint references the field by name and the
        # named index ('transcript__transcr_c204b6_idx') was generated
        # against the old column name. We drop both, rename the column,
        # and recreate them targeting the new name.
        migrations.RemoveConstraint(
            model_name='transcriptsegment',
            name='one_live_segment_per_lk_id',
        ),
        migrations.RemoveIndex(
            model_name='transcriptsegment',
            name='transcript__transcr_c204b6_idx',
        ),
        migrations.RenameField(
            model_name='transcriptsegment',
            old_name='livekit_segment_id',
            new_name='provider_segment_id',
        ),
        migrations.AddIndex(
            model_name='transcriptsegment',
            index=models.Index(
                fields=['transcript', 'provider_segment_id', 'source'],
                name='transcript__transcr_provseg_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='transcriptsegment',
            constraint=models.UniqueConstraint(
                fields=('transcript', 'provider_segment_id', 'source'),
                condition=models.Q(('source', 'live'), models.Q(('provider_segment_id', ''), _negated=True)),
                name='one_live_segment_per_provider_id',
            ),
        ),
    ]
