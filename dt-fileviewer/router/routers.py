import asyncio
import pathlib

import aiofiles
import websockets
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger as LOGGER
from starlette.datastructures import URL, FormData
from starlette.websockets import WebSocketDisconnect
from utils import cfg as cfg
from utils.helper import Helper
from utils.validation import Validation as Validator

router = APIRouter()

templates = Jinja2Templates(directory="./dt-fileviewer/templates/")
templates.env.globals['URL'] = URL


# == /root  ===============================================================================
@router.get('/')
def root(request: Request):
    if cfg.text_files_configured:
        return RedirectResponse('/viewfile')

    # Need to configure some valid endpoints
    return RedirectResponse('/configure')

# == /log_reader  ===============================================================================
@router.get("/viewfile/", response_class=HTMLResponse)
def viewfile( request: Request):
    app_info = Helper.get_app_info('viewfile')
    textfile = list(app_info['_textfiles'].keys())[0]
    app_info['_selected_textfile_nm'] = textfile 
    return templates.TemplateResponse('viewfile.html', context={'request': request, 'appinfo': app_info}) 
    
@router.post('/viewfile/{textfile}', response_class=HTMLResponse)
async def select_textfile(textfile: str, request: Request):
    app_info = Helper.get_app_info('viewfile')
    form_data: FormData = await request.form()
    LOGGER.warning(f'form_data: {form_data}')
    app_info['_selected_textfile_nm'] = textfile
    if pathlib.Path(textfile).exists() and textfile in app_info['_textfiles']:
        app_info['_valid_file_name'] = True

    return templates.TemplateResponse('viewfile.html', context={'request': request, 'appinfo': app_info}) 


# == /configure  ===============================================================================
@router.get('/configure', response_class=HTMLResponse)
def configure(request: Request):
    app_info = Helper.get_app_info('configure')
    return templates.TemplateResponse('configure.html', context={'request': request, 'appinfo': app_info, 'errors': {}})     

@router.post('/configure', response_class=HTMLResponse)
async def configure_update(request: Request):
    app_info = Helper.get_app_info('configure')
    form_data: FormData = await request.form()
    # LOGGER.warning(f'form_data: {form_data}')
    valid, changes_detected, errors, new_app_info = Validator.validate_form(app_info, form_data)
    if valid and changes_detected:
        LOGGER.info('Attempt to update configuration...')
        Helper.update_app_info(new_app_info)

    LOGGER.debug(f'new_app_info:\n{new_app_info}')
    return templates.TemplateResponse('configure.html', context={'request': request, 'appinfo': new_app_info, 'errors': errors}) 

# == /system  ===============================================================================
@router.get('/system', response_class=HTMLResponse)
def system_info(request: Request):
    app_info = Helper.get_app_info('system')
    return templates.TemplateResponse('system.html', context={'request': request, 'appinfo': app_info})     


# == /websocket  ===============================================================================
@router.websocket("/ws/log/{textfile_id}")
async def websocket_ep_log(textfile_id: str, websocket: WebSocket):
    textfile_nm = cfg.text_files.get(textfile_id, 'DoesNotExist')
    LOGGER.info('')
    LOGGER.info(f'==> websocket_ep_log("{textfile_id}")')
    textfile = pathlib.Path(textfile_nm)
    LOGGER.info(f'- {textfile_id} - resolves to: {textfile}')

    await websocket.accept()
    first_chunk = 4096
    if not textfile.exists():
        msg = f"- File [{textfile}] does not exist."
        LOGGER.error(f'{msg}  Closing connection.')
        try:
            # await websocket.send_denial_response(response)
            await websocket.close(3000, msg)
        except Exception as ex:
            LOGGER.warning(f'Close error: {ex}')
        return
    
    current_size = textfile.stat().st_size
    last_size = 0 if current_size < first_chunk else current_size - first_chunk
    LOGGER.debug(f'- [{textfile}]  Current size: {current_size}  Last size: {last_size}')
    first_line = True
    try:
        while True:
            await asyncio.sleep(1) # Poll every second
            current_size = textfile.stat().st_size
            if current_size > last_size:
                async with aiofiles.open(textfile, mode='r') as h_textfile:
                    await h_textfile.seek(last_size)
                    while new_line := await h_textfile.readline():
                        # If new line is just a blank line, new line char or empty string, skip it
                        if new_line in ["\n", "\r\n", ""] or first_line:
                            first_line = False
                            continue
                        line = Helper.filter_line(new_line)
                        await websocket.send_text(line)
                last_size = current_size

    except websockets.exceptions.ConnectionClosedOK:
        LOGGER.info('Websocket connection closed.')
    except websockets.exceptions.ConnectionClosedError as wsecce:
        LOGGER.warning(f'Websocket connection closed {wsecce}')
    except asyncio.exceptions.CancelledError:
        LOGGER.warning('Cancel requested.')
    except WebSocketDisconnect:
        LOGGER.warning('Websocket disconnected prior to being closed.')
    except Exception as e:
        LOGGER.exception(f'Exception while websocket polling. {e}')
    
    try:
        await websocket.close()
    except RuntimeError as re:
        if not str(re).startswith('Cannot call "send"'):
            LOGGER.error(f'Websocket close: {re}')
