import asyncio


class IRCClient(asyncio.Protocol):
    """Base IRC client protocol."""

    nick = 'caktus-bot'
    channel = '#caktus-test'

    def connection_made(self, transport):
        self.transport = transport
        self.closed = False
        self.send('USER %s irc.freenode.net irc.freenode.net Test IRC bot' % self.nick)
        self.send('NICK %s' % self.nick)
        self.send('JOIN %s' % self.channel)

    def data_received(self, data):
        message = data.decode('utf8', 'ignore')
        print('Received message: %s' % message)

    def connection_lost(self, exc):
        if not self.closed:
            try:
                self.transport.close()
            finally:
                self.closed = True

    def send(self, message):
        if message:
            if not message.endswith('\r\n'):
                message += '\r\n' 
            self.transport.write(message.encode('utf8'))


def main():
    """Main function for running bot."""
    loop = asyncio.get_event_loop()
    connection = loop.create_connection(IRCClient, 'irc.freenode.net', 6667)
    loop.run_until_complete(connection)
    loop.run_forever()
    loop.close()


if __name__ == '__main__':
    main()
