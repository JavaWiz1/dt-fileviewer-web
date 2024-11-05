import asyncio
import pathlib
from typing import Dict
from threading import Lock

import aiofiles
from loguru import logger as LOGGER
# from utils.helper import Helper, Message, MessageCommand
from enum import Enum
from utils.helper import Helper

class StartPos(Enum):
    HEAD = 1
    CENTER = 2
    TAIL = 3

        
class TextFileHandler():
    def __init__(self, filename):
        self.filename = pathlib.Path(filename)
        if not self.filename.exists():
            raise FileNotFoundError(f'{filename} not found.')

        self._processing = False
        self._stop_requested = False
        self._paused: bool = False

        self._tail_block_size: int = 4096
        self._buffer: list = []
        self._lock_buffer: Lock = Lock()
        self._tail_task: asyncio.Task = None

    @property
    def paused(self) -> bool:
        return self._paused
    
    @paused.setter
    def paused(self, state: bool):
        self._paused = state

    @property
    def in_progress(self) -> bool:
        return self._processing

    async def start_tail(self, start_loc: StartPos = StartPos.TAIL, filter_text: str = None ):
        LOGGER.info(f'start_tail(start_loc={start_loc}, filter_text={filter_text})')
        if self.in_progress:
            check_cnt = 0
            LOGGER.warning('- tail in progress, send stop signal...')
            self.stop_tail()
            while self.in_progress and check_cnt < 5:
                check_cnt += 1
                LOGGER.warning(f'  waiting for current tail to end.  [{check_cnt}]')
                await asyncio.sleep(.5)
        if self.in_progress:
            LOGGER.error(f'Tail in progress, cannot start new tail for [{self.filename.name}].')
            raise RuntimeError('Tail already in progress, stop_tail first!')
        
        self._tail_task = asyncio.create_task(self._tail_file(start_loc, filter_text))
        # Do we need this or will it block?
        # self._tail_task.add_done_callback(self.stop_tail)
        LOGGER.warning('tail_task STARTED.')


    async def _tail_file(self, start_loc: StartPos = StartPos.TAIL, filter_text: str = None ):
        if self._processing:
            raise RuntimeError('Tail already in progress, stop_tail first!')
        
        LOGGER.debug(f'_tail_file(start_loc={start_loc}, filter_text={filter_text})')
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

            first_line = True
            # try:
            # Loop looking for new textfile lines
            self._processing = True
            LOGGER.info(f'- Begin processing - [{self.filename}]')
            LOGGER.info(f'                     Current size: {current_size}  Last size: {last_pos}  stop_requesed: {self._stop_requested}')
            while True and not self._stop_requested:
                await asyncio.sleep(2)
                current_size = self.filename.stat().st_size
                # Get next line if file has grown, and process is NOT paused
                if current_size > last_pos and not self._paused:
                    async with aiofiles.open(str(self.filename), mode='r') as h_file:
                        if last_pos > 0:
                            LOGGER.debug(f'- seek to {last_pos}')
                            await h_file.seek(last_pos)
                        LOGGER.info('Begin read loop...')
                        while new_line := await h_file.readline():
                            chk_line = new_line.replace('\n','').replace('\r','')
                            LOGGER.trace(f'- line read: {chk_line}')
                            # If new line is just a blank line, new line char or empty string, skip it
                            if new_line in ["\n", "\r\n", ""] or (first_line and last_pos != 0):
                                # LOGGER.debug(f"Skipping: [{chk_line}]")
                                first_line = False
                                continue
                            if filter_text and filter_text not in new_line:
                                # eat this line
                                LOGGER.warning('filtering line.')
                                continue
                            
                            line = Helper.filter_line(new_line)
                            with self._lock_buffer:
                                self._buffer.append(line)
                                # LOGGER.debug(f'- buffer size: {len(self._buffer)}')

                    last_pos = current_size

        except Exception as ex:
            LOGGER.exception(repr(ex))
        
        finally:
            LOGGER.success(f'tail file completed for {self.filename}')
            self._stop_requested = False
            self._paused = False
            self._processing = False
            await asyncio.sleep(.5)
            with self._lock_buffer:
                self._buffer = []


    async def get_or_waitfor_line(self) -> str:
        line = None
        LOGGER.debug(f'get_or_waitfor_line() -  buffer_size: {len(self._buffer)} - in_process: {self.in_progress}')
        while line is None and self.in_progress:
            try:
                with self._lock_buffer:
                    line = self._buffer.pop(0)
            except IndexError:
                line = None
                await asyncio.sleep(.5)
        # response = Message(MessageCommand.OUTPUT, line)
        return line
    

    def stop_tail(self):
        self._stop_requested = True

