import asyncio
import mimetypes
import os
import time

from aiohttp import Response, EofStream
from aiohttp.server import ServerHttpProtocol
from aiohttp.websocket import do_handshake, MSG_PING, MSG_TEXT, MSG_CLOSE


class IRCClient(asyncio.Protocol):
    """Base IRC client protocol."""

    nick = 'caktus-bot'
    channel = '#caktus-test'

    def __init__(self, ws):
        self.ws = ws
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport
        self.closed = False
        self.send('USER %s irc.freenode.net irc.freenode.net Test IRC bot' % self.nick)
        self.send('NICK %s' % self.nick)
        self.send('JOIN %s' % self.channel)

    def data_received(self, data):
        message = data.decode('utf8', 'ignore')
        self.ws.send(message)

    def connection_lost(self, exc):
        self.close()

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
        print(message)

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
