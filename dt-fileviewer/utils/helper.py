from dateutil.parser import parse as dt_parser
from dt_tools.os.os_helper import OSHelper
from loguru import logger as LOGGER
from utils import cfg as cfg

# class MessageCommand:
#     OUTPUT = 'output'
#     PAUSE  = 'pause'
#     QUIT   = 'quit'

# @dataclass
# class Message():
#     command: MessageCommand
#     parm: str

#     def to_dict(self) -> dict:
#         return {'command': self.command, 'parm': self.parm}
    

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
        if len(token) > 0 and Helper.is_date(token[0]):
            # Remove date from input line
            line_in = line_in.removeprefix(f'{token[0]} ')

        line = line_in.replace(' ','&nbsp;').replace('\r','').replace('\n','')
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

        app_info:dict = {}

        include_cpu  = True if for_dialog in ['system'] else False
        include_mem  = True if for_dialog in ['system'] else False
        include_disk = True if for_dialog in ['system'] else False
        sys_info = OSHelper.sysinfo(include_cpu=include_cpu, 
                                    include_memory=include_mem,
                                    include_disk=include_disk)

        app_info = sys_info['system'].copy()
        if include_cpu:
            app_info['cpu']= sys_info['cpu']
        if include_mem:
            sys_info['memory']['virtual_total'] = OSHelper.bytes_to_printformat(sys_info['memory']['virtual_total'])
            sys_info['memory']['virtual_used']  = OSHelper.bytes_to_printformat(sys_info['memory']['virtual_used'])
            sys_info['memory']['virtual_free']  = OSHelper.bytes_to_printformat(sys_info['memory']['virtual_free'])
            sys_info['memory']['swap_total'] = OSHelper.bytes_to_printformat(sys_info['memory']['swap_total'])
            sys_info['memory']['swap_used']  = OSHelper.bytes_to_printformat(sys_info['memory']['swap_used'])
            sys_info['memory']['swap_free']  = OSHelper.bytes_to_printformat(sys_info['memory']['swap_free'])
            app_info['memory']= sys_info['memory']
        if include_disk:
            # for d_entry in sys_info["disk"]["partitions"]:
            for idx in range(len(sys_info['disk']['partitions'])):
                d_entry = sys_info['disk']['partitions'][idx]
                LOGGER.warning(d_entry)
                if len(d_entry['fstype']) > 0:
                    d_entry['total'] = OSHelper.bytes_to_printformat(d_entry['total'])
                    d_entry['used'] = OSHelper.bytes_to_printformat(d_entry['used'])
                    d_entry['free'] = OSHelper.bytes_to_printformat(d_entry['free'])
                LOGGER.warning(sys_info['disk']['partitions'][idx])
            app_info['disk']= sys_info['disk']
        
        if Helper._UNKNOWN not in cfg.text_files.values():
            textfiles = {Helper._UNKNOWN_KEY: Helper._UNKNOWN}
            textfiles.update(cfg.text_files)
        else:
            textfiles = cfg.text_files

        app_info['_textfiles'] = textfiles
        
        if for_dialog in ['viewfile']:
            app_info['_selected_textfile_nm'] = list(textfiles.values())[0]
            app_info['_valid_file_name'] = False
            app_info['_textfiles_defined'] = cfg.text_files_configured
            app_info['start_pos'] = cfg.start_pos
            app_info['filter_text'] = cfg.filter_text

        LOGGER.debug(f'app_info:\n{app_info}')
        return app_info
    
    @staticmethod
    def update_app_info(app_info: dict):
        cfg.text_files = app_info['_textfiles']
        cfg.text_files
        cfg.create_new_config(overwrite=True)
        LOGGER.success(f'Config updated with {len(cfg.text_files)} file locations')
        Helper.reload_configuration()
