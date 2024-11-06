import pathlib

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger as LOGGER
from starlette.datastructures import URL, FormData
from utils import cfg as cfg
from utils.helper import Helper
from utils.validation import Validation as Validator
from utils.ws_con_mgr import WsConnectionManager
from utils.textfile_tailer import TextFileHandler, StartPos


router = APIRouter()

templates = Jinja2Templates(directory="./dt-fileviewer/templates/")
templates.env.globals['URL'] = URL

connection: WsConnectionManager = None
tail_process: TextFileHandler = None



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

@router.websocket("/ws/view/{textfile_id}")
async def ws_view_file(textfile_id: str, websocket: WebSocket):
    textfile_nm = cfg.text_files.get(textfile_id, 'DoesNotExist')
    LOGGER.info('')
    LOGGER.info(f'==> ws_view_file("{textfile_id}")')
    textfile = pathlib.Path(textfile_nm)
    LOGGER.info(f'- {textfile_id} - resolves to: {textfile}')
    if not textfile.exists():
        LOGGER.warning('- Does NOT exist.  Ignore.')
        await websocket.close()
        return
    

    LOGGER.info('- Create tail_process')
    tail_process = TextFileHandler(textfile_nm)

    LOGGER.info('- Create connection manager')
    connection = WsConnectionManager(websocket=websocket,
                                    recv_handler=get_incoming_command,
                                    send_handler=tail_process.get_or_waitfor_line,
                                    msg_type=WsConnectionManager.MsgType.TEXT)
    
    start_pos: str = websocket.query_params.get("start_pos")
    filter_text: str = websocket.query_params.get("filter_text")    
    LOGGER.info(f'- Start  tail_process.  StartPos: {start_pos}  Filter: {filter_text}')

    await tail_process.start_tail(start_loc=StartPos[start_pos.upper()], filter_text=filter_text)

    LOGGER.info('- handle websocket request.')
    await connection.handle_connection()
    tail_process.stop_tail()


async def get_incoming_command(message: dict, cm: WsConnectionManager):
    print(f'- Received: {message}  {type(message)}')
    cmd = message.get('command', None)
    if cmd is None:
        LOGGER.error('Null command received, ignored.')
        return
    
    if cmd == 'filter':
        parms = message.get('params', None)
        LOGGER.info(f'Filter set to {parms}')
    elif cmd == 'start_pos':
        parms = message.get('params', None)
        LOGGER.info(f'start_pos set to {parms}')
    elif cmd == 'pause':
        LOGGER.info('Pause requested')
    elif cmd == 'quit':
        await cm.shutdown()
    else:
        await cm.inject_message(f'Received: {message}')        
    