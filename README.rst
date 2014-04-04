IRC Web Client using Asyncio
=======================================

This is a very basic Web Client IRC written in Python. This is a toy/experiement
and should not be used in production.

This uses the ``asyncio`` package added in Python 3.4 and ``aiohttp``. You can also install the backport
package on Python 3.3 via ``pip install asyncio``.

    mkvirtualenv web-irc -p /usr/bin/python3.4
    workon web-irc
    pip install -r requirements.txt

You can start the server from the command line via::

    python server.py

This starts the webserver on http://localhost:8000. From there you can connect to the
Freenode IRC servers and join a channel. By default it will used this ``caktus-bot``
and join ``#caktus-test``.


License
--------------------------------------

This project is released under the BSD License. See the 
`LICENSE <https://github.com/caktus/web-irc/blob/master/LICENSE>`_ file for more details.