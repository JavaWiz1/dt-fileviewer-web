import os
import pathlib
import sys

import dt_tools.logger.logging_helper as lh
import utils.cfg as cfg
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from loguru import logger as LOGGER
from router import routers
from utils.helper import Helper

SEP_LINE = '='*80

app = FastAPI()

async def lifespan(app: FastAPI):
    # Startup code
    LOGGER.info(SEP_LINE)
    config_dict = cfg.to_dict()
    for key in config_dict:
        LOGGER.info(f'== {key:20} : {config_dict[key]}')

    LOGGER.info(f'== WorkingDir           : {os.getcwd()}')
    LOGGER.info(SEP_LINE)
    if not pathlib.Path(cfg.FILE_CONFIG).exists():
        cfg.create_new_config()
        Helper.reload_configuration()
    
    LOGGER.success('>> Startup configuration complete.')
    if not cfg.text_files_configured:
        LOGGER.warning('- No files defined.')
    else:
        LOGGER.info(f'- {len(cfg.text_files)} files defined.')
        LOGGER.info('')
        LOGGER.info('  Logfile ID   Location')
        LOGGER.info('  ------------ -----------------------------------')
        for key, val in cfg.text_files.items():
            LOGGER.info(f'  {key:12} {val}')

    # Only prints if debug is enabled.
    LOGGER.debug('')
    LOGGER.debug('DEBUG is enabled.')

    LOGGER.info('')
    LOGGER.info('Waiting for connection...')
    yield

    # Shutdown/Clean up code
    LOGGER.success('>> process complete.')

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="./dt-fileviewer/static"), name="static")
app.include_router(routers.router)

@app.middleware('http')
async def middleware_hook(request: Request, call_next):
    if '/static/' not in request.url.path:
        LOGGER.warning(request.url.path)
        params = '' if len(request.path_params) == 0 else request.path_params
        LOGGER.info(f'=> {request.client.host:13} [{request.method}] {request.url}  {request.query_params}  {params}')

    response = await call_next(request)
    return response


# ==========================================================================================================
# === Main Body
# ==========================================================================================================
if __name__ == "__main__":
    console_ll = "DEBUG" if '-v' in sys.argv else cfg.console_ll
    cfg.console_ll = console_ll
    h_console = lh.configure_logger(log_level=cfg.console_ll, log_format=cfg.console_format, brightness=False)  # noqa: F841
    h_infolog = lh.configure_logger(cfg.logfile, log_level=cfg.console_ll, log_format=cfg.file_format, rotation=cfg.rotation, retention=cfg.retention)  # noqa: F841
    
    if '-c' in sys.argv:
        cfg.create_new_config()
    else:
        try:
            uvicorn.run(app='main:app', 
                        host=cfg.bind_host, 
                        port=cfg.listen_port,
                        reload=cfg.auto_reload,
                        workers=cfg.num_workers, 
                        proxy_headers=True,
                        forwarded_allow_ips='*',
                        log_level=cfg.uvicorn_ll.lower())
        except Exception as ex:
            LOGGER.exception(f'uvicorn exception: {ex}')
