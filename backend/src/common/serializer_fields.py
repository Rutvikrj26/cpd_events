"""DRF serializer field utilities.

Centralised, reusable serializer fields that solve recurring shape-mismatch
issues across the API.

Why this exists
---------------

Most of our resources have asymmetric read/write shapes: GET returns related
objects nested for client convenience (e.g. ``Event.speakers`` as a list of
full ``Speaker`` objects), while POST/PATCH expects the same field as a list
of UUIDs. SPAs that round-trip a GET response back through PATCH then break
because the write serializer cannot coerce a dict into a UUID — the user sees
``"{'uuid': '...', 'name': '...', ...}" is not a valid UUID``.

``IdOrObjectRelatedField`` is the systemic fix for that class of bug. It's a
``SlugRelatedField`` subclass whose ``to_internal_value`` accepts either a
bare scalar (UUID/PK) or a dict that contains the slug attribute, so a
round-tripped GET payload writes through unchanged.

This is one of the canonical patterns for DRF read/write asymmetry — see
https://www.django-rest-framework.org/api-guide/relations/ — and is preferred
over ``drf-writable-nested`` for this case because we don't actually want
nested *writes*; we just want the write side to be tolerant of the shape the
read side produced.
"""

from __future__ import annotations

from rest_framework import serializers


class IdOrObjectRelatedField(serializers.SlugRelatedField):
    """Slug-based related field that accepts a scalar slug *or* a dict.

    Behaviour:

    - If the incoming value is a dict, pull ``self.slug_field`` from it and
      delegate to the standard ``SlugRelatedField`` lookup. This makes the
      field tolerant of clients that round-trip a nested GET payload.
    - Otherwise behave exactly like the parent ``SlugRelatedField``.

    Output (``to_representation``) is unchanged — it still emits the scalar
    slug. If you need nested output, declare a separate read serializer or
    use ``drf-extra-fields`` ``PresentablePrimaryKeyRelatedField``.

    Example::

        speakers = IdOrObjectRelatedField(
            slug_field='uuid',
            queryset=Speaker.objects.all(),
            many=True,
            required=False,
        )

    Now both of these are valid request bodies::

        {"speakers": ["uuid-1", "uuid-2"]}                      # canonical
        {"speakers": [{"uuid": "uuid-1", "name": "Dr. ..."}]}   # round-tripped
    """

    def to_internal_value(self, data):
        if isinstance(data, dict):
            try:
                data = data[self.slug_field]
            except KeyError:
                self.fail("invalid")
        return super().to_internal_value(data)
