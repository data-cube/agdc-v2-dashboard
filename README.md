# DEA Operations Dashboard [![Build Status](https://travis-ci.org/opendatacube/dea-dashboard.svg?branch=develop)](https://travis-ci.org/opendatacubee/dea-dashboard) [![Coverage Status](https://coveralls.io/repos/github/opendatacube/dea-dashboard/badge.svg?branch=develop)](https://coveralls.io/github/opendatacube/dea-dashboard?branch=develop)

![Dashboard Screenshot](deployment/screenshot.png)

## Developer Setup


*Note*: Example server deployment directions are in the [deployment folder](deployment/README.md). 
But it will run from any typical Python WSGI server. 

These directions are for running from a local folder in development.

Firstly, install Data Cube. Use of a [Data Cube conda environment](https://datacube-core.readthedocs.io/en/latest/ops/conda.html)
is recommended.

Test that you can run `datacube system check`, and that it's connecting
to the correct instance. 

### Dependencies

Now install the dashboard dependencies:

    # These two should come from conda if you're using it, not pypi
    conda install fiona shapely
    
    # Install dependencies
    python ./setup.py develop

### Summary generation

Cache some product summaries:

    nohup python -m cubedash.generate --all &>> summary-gen.log &

(This can take a while the first time, depending on your datacube size. 
We're using `nohup .. &` to run in the background.)

### Run

Then run the app using a typical python wsgi server, for example:

    pip install gunicorn
    gunicorn -b '127.0.0.1:8080' -w 5 --timeout 300 cubedash:app

Convenience scripts are available for running in development with hot-reload (`./run-dev.sh`)
or gunicorn (`./run.sh`).

Products will begin appearing one-by-one as the summaries are generated in the background.
If impatient, you can manually navigate to a product using `/<product_name`. (Eg `/ls5_nbar_albers`) 


## FAQ


### Can I use a different datacube environment?

If you don't want to use your default configured [datacube environment](https://datacube-core.readthedocs.io/en/latest/user/config.html#runtime-config) 
(as reported by `datacube system check`), you can set environment variable 
before running the server:

    export DATACUBE_ENVIRONMENT=staging

### Can I add custom scripts or text to the page (such as analytics)?

Create one of the following `*.env.html` files:

- Global include: for `<script>` and other tags at the bottom of every page.

      cubedash/templates/include-global.env.html

- Footer text include. For human text such as Copyright statements.
  
      echo "Server <strong>staging-1.test</strong>" > cubedash/templates/include-footer.env.html

(`*.env.html` is the naming convention used for environment-specific templates: they are ignored by 
Git)

### How can I configure it?

Add a file to the current directory called `settings.env.py`

You can alter default [Flask settings](http://flask.pocoo.org/docs/1.0/config/),
as well as some cubedash-specific settings:

    # Default product to display (picks first available)
    CUBEDASH_DEFAULT_PRODUCTS = ('ls8_nbar_albers', 'ls7_nbar_albers')
    
    # Maximum search results
    CUBEDASH_HARD_SEARCH_LIMIT = 100
    
    # Include load performance metrics in http response.
    CUBEDASH_SHOW_PERF_TIMES = False
    
[Sentry](https://sentry.io/) error reporting is supported by adding a `SENTRY_CONFIG` section.
See [their documentation](https://docs.sentry.io/clients/python/integrations/flask/#settings).  

### Why aren't stylesheets updating?

The css is compiled from Sass. Run `make` to rebuild them after a change,
or use your editor to watch for changes (PyCharm will prompt to do so).

### How do I run the integration tests?
    
The integration tests run against a real postgres database, which is dropped and 
recreated between each test method:

    pytest integration_tests

#### Simple test setup

Set up a database on localhost that doesn't prompt for a password locally (eg. add credentials to `~/.pgpass`)

Then: `createdb dea_integration`

And the tests should be runnable with no configuration: `pytest integration_tests`

#### Custom test configuration

Add a `.datacube_integration.conf` file to your home directory in the same format as 
[datacube config files](https://datacube-core.readthedocs.io/en/latest/user/config.html#runtime-config).

(You might already have one if you run datacube's integration tests)

__Warning__ All data in this database will be dropped while running tests. Use a separate one from your normal 
development db.
