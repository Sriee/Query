import os
import asyncio
import signal
import json
import functools
import logging.config

logger = logging.getLogger('main')


async def echo_client(loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', 1100, loop=loop)
    try:
        while True:
            data = await reader.readline()
            if data:
                logger.info('Received from server: %s', data.decode())
                writer.write('Ack! '.format(data))
                await writer.drain()
    except asyncio.CancelledError:
        logger.debug('Stopping Co-routine')
        writer.write_eof()
    finally:
        writer.close()


def exit_handler(sig):
    logger.debug('Received signal %s' % sig)
    loop = asyncio.get_event_loop()
    loop.stop()
    loop.remove_signal_handler(signal.SIGTERM)


def main():
    _loop = asyncio.get_event_loop()
    _loop.add_signal_handler(getattr(signal, 'SIGTERM'), functools.partial(exit_handler, signal.SIGTERM))
    _loop.create_task(echo_client(_loop))
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


def setup_logging(default_path='log_config.json', default_level=logging.INFO):
    """Setup logging configuration"""

    path = default_path
    if os.path.exists(path):
        with open(path, 'r') as f:
            config = json.load(f)
        config['handlers']['file']['filename'] = os.path.abspath(os.path.join('..', 'log', 'client.log'))
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


if __name__ == '__main__':
    # Setup logging
    setup_logging(default_path=os.path.join('..', 'log_config.json'))
    logger.info('Client pid: %s', os.getpid())
    main()
