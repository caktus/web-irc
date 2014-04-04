import asyncio
import os
import time

from aiohttp import Response, EofStream
from aiohttp.server import ServerHttpProtocol
from aiohttp.websocket import do_handshake, MSG_PING, MSG_TEXT, MSG_CLOSE


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
            status, headers, parser, writer = websocket.do_handshake(
                message.method, message.headers, self.transport)

            resp = Response(self.transport, status)
            resp.add_headers(*headers)
            resp.send_headers()

            # install websocket parser
            dataqueue = self.stream.reader.set_parser(parser)

            while True:
                try:
                    msg = yield from dataqueue.read()
                except EofStream:
                    # client droped connection
                    break

                if msg.tp == MSG_PING:
                    writer.pong()

                elif msg.tp == MSG_TEXT:
                    data = msg.data.strip()
                    print('%s' % data)

                elif msg.tp == MSG_CLOSE:
                    break
        else:
            # Serve static files
            response = Response(self.transport, 200)
            response.add_header('Transfer-Encoding', 'chunked')
            response.add_header('Content-type', 'text/html')
            response.send_headers()

            path = message.path.lstrip('/') or 'index.html'

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
