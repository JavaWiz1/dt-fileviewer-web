import asyncio
import pathlib
from threading import Lock

import aiofiles
from loguru import logger as LOGGER
# from utils.helper import Helper, Message, MessageCommand
from enum import Enum
from utils.helper import Helper
from utils import cfg as cfg

class StartPos(Enum):
    HEAD = 1
    CENTER = 2
    TAIL = 3

        
class TextFileHandler():
    
    def __new__(cls, filename):
        if not hasattr(cls, 'instance'):
            LOGGER.debug('CREATING initial TextFileHandler instance.')
            cls.instance = super(TextFileHandler, cls).__new__(cls)

        return cls.instance

    def __init__(self, filename):
        LOGGER.debug('TextFileHandler() __init__')
        self.filename = pathlib.Path(filename)
        if not self.filename.exists():
            raise FileNotFoundError(f'{filename} not found.')

        self._processing = False
        self._stop_requested = False
        self._paused: bool = False

        self._tail_block_size: int = cfg.buffer_size
        self._buffer: list = []
        self._lock_buffer: Lock = Lock()
        self._tail_task: asyncio.Task = None

    @property
    def paused(self) -> bool:
        return self._paused
    
    @paused.setter
    def paused(self, state: bool):
        LOGGER.warning(f'Paused set to: {state}')
        self._paused = state

    @property
    def in_progress(self) -> bool:
        return self._processing

    async def start_tail(self, start_loc: StartPos = StartPos.TAIL, filter_text: str = None ):
        LOGGER.debug(f'start_tail(start_loc={start_loc}, filter_text={filter_text})')

        if self.in_progress:
            LOGGER.error(f'Tail in progress, cannot start new tail for [{self.filename.name}].')
            raise RuntimeError('Tail already in progress, stop_tail first!')
        
        self._tail_task = asyncio.create_task(self._tail_file(start_loc, filter_text))

    async def _tail_file(self, start_loc: StartPos = StartPos.TAIL, filter_text: str = None ):
        if self._processing:
            raise RuntimeError('Tail already in progress, stop_tail first!')
        
        LOGGER.info(f'_tail_task started for {self.filename.name}')
        # Determine starting position
        try:
            current_size = self.filename.stat().st_size
            if start_loc == StartPos.HEAD:
                last_pos = 0
            elif start_loc == StartPos.CENTER:
                last_pos = 0 if current_size < self._tail_block_size else int(current_size / 2)
            elif start_loc == StartPos.TAIL:
                last_pos = 0 if current_size < self._tail_block_size else current_size - self._tail_block_size
            else:
                last_pos = 0

            # Loop looking for new textfile lines
            first_line = True
            self._processing = True
            LOGGER.info(f'- Begin processing - [{self.filename}]  from: {start_loc.value}  filter: {filter_text}')
            LOGGER.info(f'                     Current size: {current_size}  Last size: {last_pos}  stop_requesed: {self._stop_requested}')
            while not self._stop_requested:
                await asyncio.sleep(1)
                current_size = self.filename.stat().st_size
                # Get next line if file has grown, and process is NOT paused
                if current_size > last_pos and not self.paused:
                    async with aiofiles.open(str(self.filename), mode='r') as h_file:
                        if last_pos > 0:
                            LOGGER.debug(f'- seek to {last_pos}')
                            await h_file.seek(last_pos)
                        LOGGER.info('Begin read loop...')
                        while not self._stop_requested:
                            new_line = await h_file.readline()
                            chk_line = new_line.replace('\n','').replace('\r','')
                            LOGGER.debug(f'- line read: {chk_line}')
                            # If new line is just a blank line, new line char or empty string, skip it
                            if new_line in ["\n", "\r\n", ""] or (first_line and last_pos != 0):
                                first_line = False
                                continue
                            if filter_text and filter_text not in new_line:
                                # eat this line
                                LOGGER.debug(f'- filtering line: {new_line}')
                                continue
                            
                            line = Helper.filter_line(new_line)
                            with self._lock_buffer:
                                self._buffer.append(line)
                            if len(self._buffer) > 50:
                                while len(self._buffer) > 25 and not self._stop_requested:
                                    # Don't let buffer get too far behind
                                    if not self.paused:
                                        LOGGER.info(f'- waiting for buffer to empty [{len(self._buffer)}]')
                                    await asyncio.sleep(2)

                    last_pos = current_size

        except Exception as ex:
            LOGGER.exception(repr(ex))
        
        finally:
            LOGGER.success(f'** tail file completed for {self.filename}')
            self._processing = False
            self._stop_requested = False
            self._paused = False
            await asyncio.sleep(.5)
            with self._lock_buffer:
                self._buffer = []


    async def get_or_waitfor_line(self) -> str:
        line = None
        LOGGER.debug(f'get_or_waitfor_line() -  buffer_size: {len(self._buffer)} - in_process: {self.in_progress}')
        while line is None and self.in_progress:
            if not self.paused:  # Don't get line if we are paused.
                try:
                    with self._lock_buffer:
                        line = self._buffer.pop(0)
                except IndexError:
                    line = None
            if line is None:
                await asyncio.sleep(.5)

        return line
    

    def stop_tail(self):
        LOGGER.warning('stop tail requested.')
        self._stop_requested = True

