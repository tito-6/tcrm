# WSGI Handler sample configuration file.
#
# Change the appropriate settings below, in order to provide the parameters
# that would normally be passed in the command-line.
# (at least conf['addons_path'])
#
# For generic wsgi handlers a global application is defined.
# For uwsgi this should work:
#   $ uwsgi_python --http :9090 --pythonpath . --wsgi-file tcrm-wsgi.py
#
# For gunicorn additional globals need to be defined in the Gunicorn section.
# Then the following command should run:
#   $ gunicorn tcrm.http:root --pythonpath . -c tcrm-wsgi.py

from tcrm.http import root as application  # noqa: F401
from tcrm.tools import config as conf  # noqa: F401

# ----------------------------------------------------------
# Common
# ----------------------------------------------------------

# Path to the tcrm Addons repository (comma-separated for
# multiple locations)
#conf['addons_path'] = './tcrm/addons,./addons'

# Optional database config if not using local socket
#conf['db_name'] = 'mycompany'
#conf['db_host'] = 'localhost'
#conf['db_user'] = 'foo'
#conf['db_port'] = 5432
#conf['db_password'] = 'secret'

# ----------------------------------------------------------
# Initializing the server
# ----------------------------------------------------------

application.initialize()

# ----------------------------------------------------------
# Gunicorn
# ----------------------------------------------------------
# Standard port is 8069
bind = '127.0.0.1:8069'
pidfile = '.gunicorn.pid'
workers = 4
timeout = 240
max_requests = 2000
