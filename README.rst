Basic IRC bot using Asyncio
=======================================

This is a very basic IRC bot written in Python.

This uses the asyncio package added in Python 3.4. You can also install the backport
package on Python 3.3 via ``pip install asyncio``.

    mkvirtualenv irc-bot -p /usr/bin/python3.4

You can start the bot from the command line via::

    python bot.py

It will connect as the ``caktus-bot`` nick and join the ``#caktus-test`` channel on Freenode.
