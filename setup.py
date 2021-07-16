#!/usr/bin/env python3
import os
from setuptools import find_packages, setup

tests_require = [
    "black",
    "docutils",
    "boltons",
    "deepdiff",
    "digitalearthau",
    "flake8",
    "jsonschema > 3",
    "pre-commit",
    "pytest",
    "pytest-benchmark",
    "pytest-cov",
    "requests-html",
    "raven",
    "blinker",
    "prometheus-flask-exporter",
]

extras_require = {
    "test": tests_require,
    # These are all optional but nice to have on a real deployment
    "deployment": [
        # Performance
        "ciso8601",
        "bottleneck",
        # The default run.sh and docs use gunicorn+meinheld
        "gunicorn",
        "setproctitle",
        "meinheld",
        "gevent",
        # Monitoring
        "raven",
        "blinker",
        "prometheus-flask-exporter",
    ],
}

packages = find_packages()
if os.getenv("ENVIRONMENT") == "deployment":
    packages = find_packages(exclude=("integration_tests",))

setup(
    name="datacube-explorer",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    python_requires=">=3.6",
    url="https://github.com/opendatacube/datacube-explorer",
    author="Geoscience Australia",
    author_email="earth.observation@ga.gov.au",
    packages=packages,
    include_package_data=True,
    install_requires=[
        "cachetools",
        "click",
        "dataclasses>=0.6;python_version<'3.7'",
        "datacube>=1.8",
        "eodatasets3>=0.21.1",
        "fiona",
        "flask",
        "Flask-Caching",
        "flask-cors",
        "flask_themes @ git+https://git@github.com/opendatacube/flask-themes@master",
        "geoalchemy2",
        "geographiclib",
        "jinja2",
        "pyorbital",
        "pyproj",
        "python-dateutil",
        "python-rapidjson",
        "shapely",
        "simplekml",
        "sqlalchemy>=1.3",
        "structlog",
    ],
    tests_require=tests_require,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "cubedash-gen = cubedash.generate:cli",
            "cubedash-view = cubedash.summary.show:cli",
            "cubedash-run = cubedash.run:cli",
            "cubedash-page-test = cubedash.warmup:cli",
        ]
    },
)
