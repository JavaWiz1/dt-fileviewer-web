from loguru import logger as LOGGER
from starlette.websockets import WebSocket, WebSocketState, WebSocketDisconnect
import asyncio


class WsConnectionManager():
    class MsgType:
        BYTES = 'bytes'
        JSON  = 'json'
        TEXT  = 'text'

    def __init__(self, websocket: WebSocket, recv_handler: callable, send_handler: callable, msg_type: MsgType = MsgType.TEXT):
        LOGGER.debug('ConnectionManager __init__()')
        self.websocket = websocket
        self.receiver  = recv_handler
        self.sender    = send_handler
        self._connected: bool = False
        self._msg_type = msg_type

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def handle_connection(self):
        LOGGER.debug('ConnectionManager - handler() ')
        LOGGER.debug('- create consumer and producer')
        consumer_task = asyncio.create_task(self.receive_handler(), name='consumer_task')
        producer_task = asyncio.create_task(self.send_handler(), name='producer_task')
        tasks = [consumer_task, producer_task]

        LOGGER.debug('- accept websocket connection')
        await self.websocket.accept()
        self._connected = True
        LOGGER.debug('- wait for consumer/producer to terminate')
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )
        LOGGER.info('WebSocket tasks terminating...')
        for task in tasks:
            LOGGER.debug(f'Task: {task.get_name()}  state: {task._state}')

        for task in pending:
            LOGGER.debug(f'task in CANCEL: {task.get_name()}')
            task.cancel()
        
        loop_cnt = 0
        LOGGER.info(f'Pending Tasks [{len(pending)}]:')
        still_pending = list(pending)
        while len(still_pending) > 0 and loop_cnt < 20:
            loop_cnt += 1
            for task in still_pending:
                if task._state in ['FINISHED', 'CANCELLED']:
                    still_pending.remove(task)
                    LOGGER.success(f'- Task: {task.get_name()}  state: {task._state}')
                else:
                    LOGGER.warning(f'- Task: {task.get_name()}  state: {task._state}')
                await asyncio.sleep(.25)

        self._connected = False
        LOGGER.info('handler()-exiting...')

    async def receive_handler(self):
        LOGGER.debug('ConnectionManager - receive_handler() triggered.')
        try:
            while True and self.is_connected:
                try:
                    if self.websocket.client_state != WebSocketState.CONNECTED:
                        LOGGER.error(f'- Websocked not CONNECTED [{self.websocket.client_state}], cannot receive message')
                        break
                    LOGGER.warning(f'- waiting for message [{self._msg_type}]')
                    # Can we make this smart (i.e. bytes, json, text)
                    if self.MsgType == self.MsgType.BYTES:
                        message = await self.websocket.receive_bytes()
                    elif self.MsgType == self.MsgType.JSON:
                        message = await self.websocket.receive_json()
                    elif self._msg_type == self.MsgType.TEXT:
                        message = await self.websocket.receive_text()
                    else:
                        raise TypeError(f'Invalid MsgType [{self._msg_type}]')
                    LOGGER.warning(f'- received message [{message}]')
                    await self.receiver(message, self)
                except WebSocketDisconnect:
                    LOGGER.warning('- websocket disconneted.')
                    self._connected = False
                except Exception as ex:
                    LOGGER.error(f'receive_handler (loop): {type(ex)} {ex}')
                    break
        except Exception as ex:
            LOGGER.error(f'receive_handler: {ex}')

        LOGGER.info('receive_handler()-exiting...')

    async def send_handler(self):
        LOGGER.debug('ConnectionManager - send_handler() triggered.')
        try:
            while True and self.is_connected:
                message = await self.sender()
                LOGGER.debug(f'- received: {message}')
                await asyncio.sleep(.1)
                if message is not None:
                    if self.websocket.client_state != WebSocketState.CONNECTED:
                        LOGGER.error(f'- Websocked not CONNECTED [{self.websocket.client_state}], cannot send message: {message}')
                        break
                    if self.MsgType == self.MsgType.BYTES:
                        await self.websocket.send_bytes(message)
                    elif self.MsgType == self.MsgType.JSON:
                        await self.websocket.send_json(message)
                    elif self._msg_type == self.MsgType.TEXT:
                        await self.websocket.send_text(message)
                    else:
                        raise TypeError(f'Invalid MsgType [{self._msg_type}]')
        except WebSocketDisconnect:
            LOGGER.warning('- websocket disconneted.')
            self._connected = False
        except Exception as ex:
            LOGGER.error(f'send_handler: {ex}')

        LOGGER.warning('send_handler()-exiting...')
                
    async def inject_message(self, message):
        LOGGER.debug(f'- inject_message: {message}')
        if self.websocket.client_state == WebSocketState.CONNECTED:
            if self.MsgType == self.MsgType.BYTES:
                await self.websocket.send_bytes(message)
            elif self.MsgType == self.MsgType.JSON:
                await self.websocket.send_json(message)
            elif self._msg_type == self.MsgType.TEXT:
                await self.websocket.send_text(message)
            else:
                raise TypeError(f'Invalid MsgType [{self._msg_type}]')
            
            return
        
        LOGGER.error(f'- Websocked not CONNECTED [{self.websocket.client_state}], cannot inject message: {message}')

    async def shutdown(self):
        LOGGER.debug('Shutdown request received.')
        await self.websocket.close()
        LOGGER.warning('shutdown()-exiting...')
