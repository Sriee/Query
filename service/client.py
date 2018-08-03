import socket
import argparse
from helper import *

logger = logging.getLogger('main')


class Client(object):

    def __init__(self, name, host, port, subscription):
        self._name = name
        self._host = host
        self._port = port
        self._subscription = subscription

    @property
    def name(self):
        return self._name

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def subscription(self):
        return self._subscription

    async def listener(self, loop):
        reader, writer = await asyncio.open_connection(host=self.host, port=self.port, loop=loop)
        logger.debug('%s @%s', self.name, writer.transport.get_extra_info('sockname'))

        try:
            # Handshake between server and client
            logger.info('Sending %s hello message to server.', self.name)
            await send_msg(writer, self.name + ' hello')

            logger.info('Waiting for hello message from server')
            message = await read_msg(reader)

            if message and message.lower() == 'hello':
                logger.info('Received reply from server. Sending Subscription...')
                await send_msg(writer, self.subscription[0])

            while True:
                data = await read_msg(reader)
                if data:
                    logger.info('Received from server: %s', data)

        except asyncio.CancelledError:
            logger.debug('Stopping Co-routine')
            writer.write_eof()
        finally:
            writer.close()

    def run(self):
        _loop = asyncio.get_event_loop()
        _loop.add_signal_handler(getattr(signal, 'SIGTERM'), exit_handler)
        _loop.create_task(self.listener(_loop))
        try:
            logger.debug('Starting client event loop')
            _loop.run_forever()
        finally:
            logger.debug('Event loop terminated.')
            tasks = asyncio.Task.all_tasks()
            group = asyncio.gather(*tasks, return_exceptions=True)
            group.cancel()
            _loop.run_until_complete(group)
            _loop.close()

    def __str__(self):
        return 'Client \'{}\' Status:\nConnected to Server: {}@{}\nSubscriptions: {}'\
            .format(self.name, self.host, self.port, ', '.join(self.subscription))


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description='''
                                  Client application to receive machine state notification from the server. 
                                  Client should subscribe to the required states that it requires the notification
                                  ''')
    cli.add_argument('--host', help='Host IP of the server', default='127.0.0.1')
    cli.add_argument('--port', type=int, help='Port in which server is listening to', default=1200)
    cli.add_argument('--name', help='Name of the client', default=socket.gethostname())
    cli.add_argument('--sub', choices=['Pending', 'Imaging', 'Executing', 'Error', 'Completed', 'Suspended'],
                     nargs='+', default=['Error'], help='Client subscription state')
    args = cli.parse_args()

    # Client name should be lesser than 15 characters
    if len(args.name) > 15:
        args.name = args.name[:16]

    # Setup logging
    setup_logging(log_name=os.path.abspath(os.path.join('log', args.name + '.log')))
    logger.info('Client pid: %s', os.getpid())
    logger.info(args)
    this = Client(name=args.name, host=args.host, port=args.port, subscription=args.sub)
    this.run()
