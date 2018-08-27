from __future__ import absolute_import

import flask
import structlog
from flask_caching import Cache
from pathlib import Path
from typing import Iterable, Tuple
from typing import Optional

from cubedash.summary import TimePeriodOverview, FileSummaryStore
from datacube.index import Index
from datacube.index import index_connect
from datacube.model import DatasetType

NAME = 'cubedash'

app = flask.Flask(NAME)
cache = Cache(
    app=app,
    config={'CACHE_TYPE': 'simple'}
)


# Thread and multiprocess safe.
# As long as we don't run queries (ie. open db connections) before forking
# (hence validate=False).
index: Index = index_connect(application_name=NAME, validate_connection=False)

# Pre-computed summaries of products (to avoid doing them on page load).
SUMMARIES_DIR = Path(__file__).parent.parent / 'product-summaries'

# TODO: Proper configuration?
DEFAULT_STORE = FileSummaryStore(index, SUMMARIES_DIR)
# Which product to show by default when loading '/'. Picks the first available.
DEFAULT_START_PAGE_PRODUCTS = ('ls7_nbar_scene', 'ls5_nbar_scene')

_LOG = structlog.get_logger()


@cache.memoize(timeout=60)
def get_summary(
        product_name: str,
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None) -> Optional[TimePeriodOverview]:
    return DEFAULT_STORE.get(product_name, year, month, day)


@cache.memoize(timeout=120)
def get_last_updated():
    return DEFAULT_STORE.get_last_updated()


@cache.memoize(timeout=120)
def get_products_with_summaries() -> Iterable[Tuple[DatasetType, TimePeriodOverview]]:
    """
    The list of products that we have generated reports for.
    """
    products = [
        (index.products.get_by_name(product_name), get_summary(product_name))
        for product_name in DEFAULT_STORE.list_complete_products()
    ]
    if not products:
        raise RuntimeError(
            'No product reports. '
            'Run `python -m cubedash.generate --all` to generate some.'
        )

    return products
