import asyncio
import json
import mimetypes
import os
import re
import time

from aiohttp import Response, EofStream
from aiohttp.server import ServerHttpProtocol
from aiohttp.websocket import do_handshake, MSG_PING, MSG_TEXT, MSG_CLOSE


COMMANDS = {
    'ping': re.compile(r'PING :(?P<data>.*)'),
    'join': re.compile(r':(?P<nick>\S+)!\S+@\S+ JOIN (?P<channel>\S+)'),
    'message': re.compile(r':(?P<nick>\S+)!\S+@\S+ PRIVMSG (?P<target>\S+) :\s*(?P<data>\S+.*)$'),
    'names': re.compile(r':(?P<mask>\S+) 353 (?P<nick>\S+) @ (?P<channel>\S+) :\s*(?P<names>.*)\s:(?P=mask) 366'),
    'notice': re.compile(r':(?P<nick>\S+)!\S+@\S+ NOTICE (?P<target>\S+) :\s*(?P<data>\S+.*)$'),
    'quit': re.compile(r':(?P<nick>\S+)!\S+@\S+ QUIT :\s*(?P<data>\S+.*)$'),
}

class IRCClient(asyncio.Protocol):
    """Base IRC client protocol."""

    def __init__(self, ws):
        self.ws = ws
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport
        self.closed = False
        self.nick = None
        self.channel = None
        self.joined = False
        self.ws.send(json.dumps({'status': 'connected'}))

    def data_received(self, data):
        message = data.decode('utf8', 'ignore')
        handled = False
        for cmd, regex in COMMANDS.items():
            match = regex.match(message)
            if match:
                func = getattr(self, 'on_%s' % cmd, None)
                if func is not None:
                    func(**match.groupdict())
                    handled = True
                    break
        if not handled:
            self.ws.send(message)

    def connection_lost(self, exc):
        self.close()
        self.ws.send(json.dumps({'status': 'disconnected'}))

    def on_join(self, nick, channel):
        if channel == self.channel:
            if nick == self.nick:
                self.joined = True
                self.ws.send(json.dumps({'status': 'joined', 'channel': channel}))
            else:
                self.ws.send(json.dumps({'member': nick, 'action': 'add'}))

    def on_message(self, nick, target, data):
        self.ws.send(json.dumps({
            'nick': nick,
            'target': target,
            'message': data,
        }))

    def on_names(self, mask, nick, channel, names):
        if channel == self.channel and nick == self.nick:
            for member in names.split(' '):
                self.ws.send(json.dumps({
                    'member': member.lstrip('@').lstrip('+'),
                    'action': 'add'
                }))

    def on_notice(self, nick, target, data):
        self.ws.send(json.dumps({
            'nick': nick,
            'target': target,
            'notice': data,
        }))

    def on_ping(self, data):
        self.send('PONG %s' % data)

    def on_quit(self, nick, data):
        self.ws.send(json.dumps({'member': nick, 'action': 'remove'}))

    def send(self, message):
        if message:
            if not message.endswith('\r\n'):
                message += '\r\n' 
            self.transport.write(message.encode('utf8'))

    def close(self):
        if not self.closed:
            try:
                self.transport.close()
            finally:
                self.closed = True

    def login(self, username, channel, nick=None, password=None):
        self.nick = nick or username
        self.channel = channel
        if password is not None:
            self.send('PASS %s' % password)
        self.send('USER %s irc.freenode.net irc.freenode.net Test IRC WebClient' % username)
        self.send('NICK %s' % self.nick)
        self.send('JOIN %s' % self.channel)

    def message(self, message):
        # TODO: Handle message when the connection has closed.
        if self.joined:
            self.send('PRIVMSG {0} :{1}'.format(self.channel, message))


class WebClient(object):
    """Encapsulation of client logic."""

    def __init__(self, loop, reader, writer):
        self.loop = loop
        self.reader = reader
        self.writer = writer

    @asyncio.coroutine
    def run(self):
        """Main loop for reading from the socket and delegating messages."""
        _, self.irc = yield from self.loop.create_connection(lambda: IRCClient(ws=self), 'irc.freenode.net', 6667)
        while True:
            try:
                msg = yield from self.reader.read()
            except EofStream:
                # client droped connection
                break
            else:
                if msg.tp == MSG_PING:
                    self.writer.pong()
                elif msg.tp == MSG_TEXT:
                    data = msg.data.strip()
                    self.on_message(data)
                elif msg.tp == MSG_CLOSE:
                    break
        self.irc.close()

    def on_message(self, message):
        """Handle incoming message from the socket."""
        try:
            data = json.loads(message)
        except ValueError:
            print('Received non-JSON message: %s' % message)
        else:
            if 'action' in data:
                action = data.pop('action')
                if action == 'login':
                    self.irc.login(**data)
            elif 'message' in data:
                # Pass message to IRC connection
                self.irc.message(data['message'])

    def send(self, message):
        """Send message to the websocket."""
        self.writer.send(message.encode('utf8'))


class HttpServer(ServerHttpProtocol):

    @asyncio.coroutine
    def handle_request(self, message, payload):
        now = time.time()
        upgrade = False
        for hdr, val in message.headers:
            if hdr == 'UPGRADE':
                upgrade = 'websocket' in val.lower()
                break

        if upgrade:
            # websocket handshake
            status, headers, parser, writer = do_handshake(
                message.method, message.headers, self.transport)

            resp = Response(self.transport, status)
            resp.add_headers(*headers)
            resp.send_headers()

            # install websocket parser
            reader = self.stream.set_parser(parser)
            client = WebClient(self._loop, reader, writer)
            yield from client.run()
        else:
            # Serve static files
            response = Response(self.transport, 200)
            response.add_header('Transfer-Encoding', 'chunked')


            path = message.path.lstrip('/') or 'index.html'
            content_type, _ = mimetypes.guess_type(path)

            response.add_header('Content-type', content_type or 'text/html')
            response.send_headers()

            try:
                with open(os.path.join('static', path), 'rb') as fp:
                    chunk = fp.read(8196)
                    while chunk:
                        if not response.write(chunk):
                            break
                        chunk = fp.read(8196)
            except OSError:
                drain = super().handle_request(message, payload)
            else:
                drain = response.write_eof()
                if response.keep_alive():
                    self.keep_alive(True)
                self.log_access(message, None, response, time.time() - now)
            return drain


def main():
    """Main function for running the server from the command line."""
    loop = asyncio.get_event_loop()
    factory = loop.create_server(lambda: HttpServer(debug=True, keep_alive=75), '127.0.0.1', 8000)
    server = loop.run_until_complete(factory)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
