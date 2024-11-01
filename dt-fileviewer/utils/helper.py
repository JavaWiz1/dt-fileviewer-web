from dateutil.parser import parse as dt_parser
from dt_tools.os.os_helper import OSHelper
from loguru import logger as LOGGER
from utils import cfg as cfg


class Helper:
    _UNKNOWN_KEY = 'not_selected'
    _UNKNOWN = 'Select a file to view'

    @staticmethod
    def reload_configuration():
        LOGGER.info('- reload cfg.py')
        import importlib
        importlib.reload(cfg)

    @staticmethod
    def filter_line(line_in: str) -> str:
        LOGGER.trace(f'filter_line("{line_in}")')
        token = line_in.split()
        if Helper.is_date(token[0]):
            # Remove date from input line
            line_in = line_in.removeprefix(f'{token[0]} ')

        line = line_in.replace(' ','&nbsp;')
        color_class = "text-white"
        if line.__contains__("ERROR") or line.__contains__("CRITICAL"):
            color_class = "text-danger"
        elif line.__contains__("WARNING"):
            color_class = "text-warning"
        elif line.__contains__("SUCCESS"):
            color_class = "text-success"
        elif line.__contains__("DEBUG"):
            color_class = "text-primary"

        line_out = f'<span class="{color_class}">{line}</span></br>'
        return line_out

    @staticmethod
    def is_date(in_token: str, fuzzy=False) -> bool:
        LOGGER.trace(f'is_date("{in_token}", {fuzzy})')
        try: 
            dt_parser(in_token, fuzzy=fuzzy)
            return True

        except ValueError:
            return False
            
    @staticmethod
    def get_app_info(for_dialog: str = '') -> dict:
        LOGGER.trace(f'get_app_info("{for_dialog}")')

        include_cpu = True if for_dialog == 'system' else False

        sys_info = OSHelper.sysinfo(include_cpu=include_cpu)

        app_info:dict = {}
        app_info = sys_info['system'].copy()
        if include_cpu:
            app_info.update(sys_info['cpu'])
        
        if Helper._UNKNOWN not in cfg.text_files.values():
            textfiles = {Helper._UNKNOWN_KEY: Helper._UNKNOWN}
            textfiles.update(cfg.text_files)
        else:
            textfiles = cfg.text_files

        app_info['_textfiles'] = textfiles
        app_info['_selected_textfile_nm'] = list(textfiles.values())[0]
        app_info['_valid_file_name'] = False
        app_info['_textfiles_defined'] = cfg.text_files_configured

        LOGGER.debug(f'app_info:\n{app_info}')
        return app_info
    
    @staticmethod
    def update_app_info(app_info: dict):
        cfg.text_files = app_info['_textfiles']
        cfg.text_files
        cfg.create_new_config(overwrite=True)
        LOGGER.success(f'Config updated with {len(cfg.text_files)} file locations')
        Helper.reload_configuration()
