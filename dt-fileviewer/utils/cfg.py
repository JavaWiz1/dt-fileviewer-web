import configparser
import pathlib
import sys
from typing import Tuple, Dict

import dt_tools.logger.logging_helper as lh
from loguru import logger as LOGGER

TEXTFILES_SECTION = 'TEXTFILES'

def _get_textfile_section() -> Dict:
    from utils.helper import Helper
    LOGGER.trace('cfg - Getting text file definitions...')
    logfiles = {}
    if not _CONFIG.has_section(TEXTFILES_SECTION):
        LOGGER.trace(f'- adding section [{TEXTFILES_SECTION}]')
        _CONFIG.add_section(TEXTFILES_SECTION)

    for option in _CONFIG[TEXTFILES_SECTION]:
        if option != Helper._UNKNOWN_KEY:
            LOGGER.trace(f'- {option}')
            logfiles[option] = (_CONFIG.get(TEXTFILES_SECTION, option))

    if len(logfiles) == 0:
        LOGGER.error(f'- No files configured, you must edit {pathlib.Path(FILE_CONFIG).absolute()} to setup.')
    return logfiles

def _get_section_desc(key: str) -> Tuple[str, str]:
    entry = _KEYWORD_SECTIONS.get(key, None)
    if entry is None:
        raise KeyError(f"'{key}' does NOT exist in _KEYWORD_SECTIONS")

    section = entry['section']
    desc = entry['desc'] 
    return section, desc

def to_dict() -> dict:
    """Return config entries as a dictionary"""
    config_dict = {}
    h_module = sys.modules[__name__]
    config_keys = [ item for item in dir(h_module) if not item.startswith('_') ]
    for key in config_keys:
        val = h_module.__getattribute__(key)
        var_type = type(val)
        if var_type is str or var_type is int or var_type is bool:
            if 'pass' in key:
                val = '*****'
            config_dict[key] = val
            
    return config_dict

def create_new_config(overwrite: bool = False):
    from utils.helper import Helper

    filename = pathlib.Path(f'./config/{PACKAGE_NAME}.cfg').absolute()
    if filename.exists() and not overwrite:
        filename = pathlib.Path(f'./config/{PACKAGE_NAME}_NEW.cfg').absolute()
    if not filename.parent.exists():  
        LOGGER.info(f'Creating directory: {filename.parent}')
        filename.parent.mkdir()

    new_config = configparser.ConfigParser(interpolation=None)
    notes = []
    this_module = sys.modules[__name__]
    for keyword in _KEYWORD_SECTIONS.keys():
        section, desc = _get_section_desc(keyword)
        if not new_config.has_section(section):
            new_config[section] = {}
        if len(desc) > 0:
            notes.append(f'# - {keyword:25} : {desc}\n')
        val = getattr(this_module, keyword, "TBD")
        new_config[section][keyword] = str(val)

    new_config.add_section(TEXTFILES_SECTION)
    for fileid, fileloc in text_files.items():
        if fileid != Helper._UNKNOWN_KEY:
            new_config[TEXTFILES_SECTION][fileid] = fileloc

    with open(filename, 'w',) as h_file:
        h_file.write(f'# {"="*80}\n')
        h_file.write(f'# {PACKAGE_NAME} configuration file (auto-generated)\n')
        h_file.write(f'# {"-"*80}\n')
        h_file.write('# NOTES:\n')
        for line in notes:
            h_file.write(line)
        h_file.write(f'# {"="*80}\n')

        new_config.write(h_file)
        for section in _CONFIG.sections():
            if section == TEXTFILES_SECTION:
                if len(_CONFIG[section].keys()) == 0:
                    h_file.write('# List of text files.  Unique ID and location of text file.\n')
                    h_file.write('# textfile_id = location of text file\n')
                    break

    LOGGER.info(f'Config file [{filename}] created/updated.')
    LOGGER.info('')

def update_config(app_info: dict):
    
    pass

# == Load _CONFIG object =================================================================
PACKAGE_NAME = 'dt-fileviewer'
FILE_CONFIG = f'./config/{PACKAGE_NAME}.cfg'

if not pathlib.Path(FILE_CONFIG).exists():
    LOGGER.error(f'Config file ({FILE_CONFIG}) does not exist. Rerun with -c')

_CONFIG = configparser.ConfigParser()
if pathlib.Path(FILE_CONFIG).exists():
    _CONFIG.read(FILE_CONFIG)

# ========================================================================================
_KEYWORD_SECTIONS = {
    "bind_host":   {"section": "WEBSERVER", "desc": "Allowed hosts (0.0.0.0 = all)"},
    "listen_port": {"section": "WEBSERVER", "desc": "Port server is listening on"},
    "auto_reload": {"section": "WEBSERVER", "desc": "Auto reload server on code file change"},
    "num_workers": {"section": "WEBSERVER", "desc": "Number of thread workers"},

    "rotation":       {"section": "LOGS", "desc": "Limit on log file size (i.e. '15 mb')"},
    "retention":      {"section": "LOGS", "desc": "How many copies to retain (i.e. 3)"},
    "logfile":        {"section": "LOGS", "desc": ""},
    "uvicorn_ll":     {"section": "LOGS", "desc": "Log level for uvicorn logging"},
    "console_ll":     {"section": "LOGS", "desc": "Log level for console logging"},
    "file_format":    {"section": "LOGS", "desc": "Log line format for console logging"},
    "console_format": {"section": "LOGS", "desc": "Log line format for console logging"},
}

# ========================================================================================
# When adding variable, also add to _KEYWORD_SECTIONS
bind_host   = _CONFIG.get(_get_section_desc('bind_host')[0],      "bind_host", fallback='0.0.0.0')
listen_port = _CONFIG.getint(_get_section_desc('listen_port')[0], "listen_port", fallback=8000)
auto_reload = _CONFIG.getboolean(_get_section_desc('auto_reload')[0], "auto_reload", fallback=False)
num_workers = _CONFIG.getint(_get_section_desc('num_workers')[0], "num_workers", fallback=1) 
   
rotation    = _CONFIG.get(_get_section_desc('rotation')[0],     "rotation", fallback='1 MB')
retention   = _CONFIG.getint(_get_section_desc('retention')[0], "retention", fallback=5)
logfile     = _CONFIG.get(_get_section_desc('logfile')[0],      "logfile", fallback=f'./logs/{PACKAGE_NAME}.log')
uvicorn_ll  = _CONFIG.get(_get_section_desc('uvicorn_ll')[0],   "uvicorn_ll", fallback="ERROR").lower()
console_ll  = _CONFIG.get(_get_section_desc('console_ll')[0],   "console_ll", fallback="INFO")
file_format    = _CONFIG.get(_get_section_desc('file_format')[0], "file_format", fallback=lh.DEFAULT_FILE_LOGFMT)
console_format = _CONFIG.get(_get_section_desc('console_format')[0], "console_format", fallback=lh.DEFAULT_DEBUG_LOGFMT)

text_files: dict       = _get_textfile_section()
text_files_configured: bool = True if len(text_files.keys()) > 0 else False