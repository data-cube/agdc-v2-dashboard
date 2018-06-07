# -*- coding: utf-8 -*-
"""
Common global filters and util methods.
"""

from __future__ import absolute_import
from __future__ import division

import collections
import functools
import pathlib
from collections import defaultdict

import structlog
from datetime import datetime, timedelta

from datacube.index.postgres._fields import RangeDocField, PgDocField
from datacube.model import Range, DatasetType, Dataset
from dateutil.relativedelta import relativedelta
from werkzeug.datastructures import MultiDict
from dateutil import tz
import shapely.geometry
import shapely.validation
from shapely.geometry import Polygon
from typing import Tuple, Optional
from flask import jsonify
from datacube.utils import jsonify_document
from datacube.utils.geometry import CRS


DEFAULT_PLATFORM_END_DATE = {
    'LANDSAT_8': datetime.now() - relativedelta(months=2),
    'LANDSAT_7': datetime.now() - relativedelta(months=2),
    'LANDSAT_5': datetime(2011, 11, 30),
}

_LOG = structlog.get_logger()


def group_field_names(request: dict) -> dict:
    """
    In a request, a dash separates field names from a classifier (eg: begin/end).

    Group the query classifiers by field names.

    >>> group_field_names({'lat-begin': '1', 'lat-end': '2', 'orbit': 3})
    {'lat': {'begin': '1', 'end': '2'}, 'orbit': {'val': 3}}
    """
    out = defaultdict(dict)

    for field_expr, val in request.items():
        comps = field_expr.split('-')
        field_name = comps[0]

        if len(comps) == 1:
            constraint = 'val'
        elif len(comps) == 2:
            constraint = comps[1]
        else:
            raise ValueError('Corrupt field name ' + field_expr)

        # Skip empty values
        if val is None or val == '':
            continue

        out[field_name][constraint] = val
    return dict(out)


def query_to_search(request: MultiDict, product: DatasetType) -> dict:
    args = _parse_url_query_args(request, product)

    # If their range is backwards (high, low), let's reverse it.
    # (the intention is "between these two numbers")
    for key in args:
        value = args[key]
        if isinstance(value, Range):
            if value.begin is not None and value.end is not None:
                if value.end < value.begin:
                    args[key] = Range(value.end, value.begin)

    return args


def dataset_label(dataset):
    """
    :type dataset: datacube.model.Dataset
    :rtype: str
    """
    # Identify by label if they have one
    label = dataset.metadata.fields.get('label')
    if label is not None:
        return label
    # Otherwise by the file/folder name if there's a path.
    elif dataset.local_uri:
        p = pathlib.Path(dataset.local_uri)
        if p.name in ('ga-metadata.yaml', 'agdc-metadata.yaml'):
            return p.parent.name

        return p.name
    # TODO: Otherwise try to build a label from the available fields?
    return str(dataset.id)


def _next_month(date: datetime):
    if date.month == 12:
        return datetime(date.year + 1, 1, 1)

    return datetime(date.year, date.month + 1, 1)


def as_time_range(year: Optional[int] = None,
                  month: Optional[int] = None,
                  day: Optional[int] = None) -> Optional[Range]:
    if year and month and day:
        start = datetime(year, month, day)
        return Range(start, start + timedelta(days=1))
    if year and month:
        start = datetime(year, month, 1)
        return Range(start, _next_month(start))
    if year:
        start = datetime(year, 1, 1)
        return Range(start, datetime(year + 1, 1, 1))
    return None


def _parse_url_query_args(request: MultiDict, product: DatasetType) -> dict:
    """
    Convert search arguments from url query args into datacube index search parameters
    """
    query = {}

    field_groups = group_field_names(request)

    for field_name, field_vals in field_groups.items():
        field = product.metadata_type.dataset_fields.get(field_name)
        if not field:
            raise ValueError("No field %r for product %s" % (field_name, product.name))

        if isinstance(field, RangeDocField):
            parser = field.lower.parse_value
        elif isinstance(field, PgDocField):
            parser = field.parse_value
        else:
            parser = lambda a: a

        if 'val' in field_vals:
            query[field_name] = parser(field_vals['val'])
        elif 'begin' in field_vals or 'end' in field_vals:
            begin, end = field_vals.get('begin'), field_vals.get('end')
            query[field_name] = Range(parser(begin) if begin else None,
                                      parser(end) if end else None)
        else:
            raise ValueError('Unknown field classifier: %r' % field_vals)

    return query


def default_utc(d: datetime) -> datetime:
    if d.tzinfo is None:
        return d.replace(tzinfo=tz.tzutc())
    return d


def now_utc() -> datetime:
    return default_utc(datetime.utcnow())


def as_json(o):
    return jsonify(jsonify_document(o))


def get_ordered_metadata(metadata_doc):
    def get_property_priority(ordered_properties, keyval):
        key, val = keyval
        if key not in ordered_properties:
            return 999
        return ordered_properties.index(key)

    # Give the document the same order as eo-datasets. It's far more readable (ID/names first, sources last etc.)
    ordered_metadata = collections.OrderedDict(
        sorted(metadata_doc.items(),
               key=functools.partial(get_property_priority, EODATASETS_PROPERTY_ORDER))
    )

    # Order any embedded ones too.
    if 'lineage' in ordered_metadata:
        ordered_metadata['lineage'] = collections.OrderedDict(
            sorted(ordered_metadata['lineage'].items(),
                   key=functools.partial(get_property_priority, EODATASETS_LINEAGE_PROPERTY_ORDER))
        )

        if 'source_datasets' in ordered_metadata['lineage']:
            for type_, source_dataset_doc in ordered_metadata['lineage']['source_datasets'].items():
                ordered_metadata['lineage']['source_datasets'][type_] = get_ordered_metadata(source_dataset_doc)

    # Products have an embedded metadata doc (subset of dataset metadata)
    if 'metadata' in ordered_metadata:
        ordered_metadata['metadata'] = get_ordered_metadata(ordered_metadata['metadata'])
    return ordered_metadata


EODATASETS_PROPERTY_ORDER = ['id', 'ga_label', 'name', 'description', 'product_type', 'metadata_type',
                             'product_level', 'product_doi',
                             'creation_dt', 'size_bytes', 'checksum_path',
                             'platform', 'instrument', 'format', 'usgs',
                             'rms_string', 'acquisition', 'extent', 'grid_spatial', 'gqa', 'browse', 'image', 'lineage',
                             'product_flags']
EODATASETS_LINEAGE_PROPERTY_ORDER = ['algorithm', 'machine', 'ancillary_quality', 'ancillary', 'source_datasets']


def dataset_shape(ds: Dataset) -> Tuple[Optional[Polygon], bool]:
    """
    Get a usable extent from the dataset (if possible), and return
    whether the original was valid.
    """
    log = _LOG.bind(dataset_id=ds.id)
    try:
        extent = ds.extent
    except AttributeError:
        # `ds.extent` throws an exception on telemetry datasets,
        # as they have no grid_spatial. It probably shouldn't.
        return None, False

    if extent is None:
        log.warn('invalid_dataset.empty_extent')
        return None, False

    geom = shapely.geometry.asShape(extent.to_crs(CRS('EPSG:4326')))

    if not geom.is_valid:
        log.warn(
            'invalid_dataset.invalid_extent',
            reason_text=shapely.validation.explain_validity(geom)
        )
        # A zero distance may be used to “tidy” a polygon.
        clean = geom.buffer(0.0)
        assert clean.geom_type == 'Polygon'
        assert clean.is_valid
        return clean, False

    if geom.is_empty:
        _LOG.warn(
            'invalid_dataset.empty_extent_geom',
            dataset_id=ds.id
        )
        return None, False

    return geom, True
