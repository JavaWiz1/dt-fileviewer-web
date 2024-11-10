import pathlib
from typing import Dict, Tuple
from starlette.datastructures import FormData
from loguru import logger as LOGGER


class Validation:

    @staticmethod
    def validate_form(app_info: dict, form_data: FormData) -> Tuple[bool, Dict[str, str], Dict[str, str]]:
        """
        Validate the Log Viewer configuration form

        Args:
            app_info (dict): Application Info
            form_data (FormData): Submitted Form Data

        Returns:
            Tuple[bool, Dict[str, str], Dict[str, str]]: rc, errors, new_app_info
        """
        LOGGER.warning('== Validate Form ====================================')
        LOGGER.debug('FormData:')
        for key, value in form_data.items():
            LOGGER.debug(f'  {key:15} {value}')

        add_fileid  = form_data.get('add_fileid')
        add_fileloc = form_data.get('add_fileloc', default='')

        upd_success, upd_chgs_detected, upd_errors, app_info = Validation.validate_upd_entries(app_info, form_data)
        del_success, del_chgs_detected, del_errors, app_info = Validation.validate_del_entries(app_info, form_data)
        add_success, add_chgs_detected, add_errors, app_info = Validation.validate_new_entry(add_fileid, add_fileloc, app_info)
        
        errors: dict = {}
        errors.update(del_errors)
        errors.update(add_errors)
        errors.update(upd_errors)
        success = upd_success and del_success and add_success
        chgs_detected = upd_chgs_detected or del_chgs_detected or add_chgs_detected

        LOGGER.log("SUCCESS" if success else "WARNING", f"== Validate Form ==> Changes: {chgs_detected}, {len(errors.keys())} errors detected.  {errors}")
        return success, chgs_detected, errors, app_info


    @staticmethod
    def validate_upd_entries(app_info: dict, form_data: FormData) -> Tuple[bool, bool, Dict[str, str], Dict[str, str]]:
        """
        Validate updates to existing Log View entries.

        Args:
            app_info (dict): Application Info dict
            form_data (FormData): Form Data

        Returns:
            Tuple[bool, Dict[str, str], Dict[str, str]]: rc, chgs_detected, errors, new_app_info
        """
        valid = True
        changes_detected = False
        errors = {}
        new_app_info: dict = app_info.copy()
        textfiles: dict = new_app_info['_textfiles'].copy()
        LOGGER.info(f'validate_upd_entries() - {len(textfiles)} entries.')        
        entry: dict = {}
        for form_text_fileid in form_data.keys():
            if form_text_fileid.startswith('upd_') and form_text_fileid.endswith('_logloc'):  # Only the update entries
                text_fileid = form_text_fileid.removeprefix('upd_').removesuffix('_logloc')
                text_fileloc = textfiles.get(text_fileid, None)
                form_fileloc = form_data.get(form_text_fileid)
                if text_fileloc is not None and text_fileloc != form_fileloc:
                    changes_detected = True
                    LOGGER.info(f'- form field: {form_text_fileid}')
                    LOGGER.info(f'  old: {text_fileloc}  new: {form_fileloc}')
                    entry['id'] = [form_text_fileid, text_fileid, text_fileid]
                    entry['loc'] = [form_text_fileid, form_fileloc, text_fileid]
                    entry_errors = Validation._validate_entry(entry, textfiles, True)
                    if len(entry_errors.keys()) > 0:
                        valid = False
                        errors.update(entry_errors)
                    else:
                        LOGGER.info(f' - field: {form_text_fileid} Update {text_fileid} from: {text_fileloc} to {form_fileloc}')
                else:
                    LOGGER.info(f'- form field: {form_text_fileid} - no change')
                
                textfiles[text_fileid] = form_fileloc

        new_app_info['_textfiles'] = textfiles
        LOGGER.log(f'{"SUCCESS" if valid else "ERROR"}', f'  rc: {valid}, chgs: {changes_detected}, errors: {errors} - {len(textfiles)} entries.')
        return valid, changes_detected, errors, new_app_info
    

    @staticmethod
    def validate_del_entries(app_info: dict, form_data: FormData) -> Tuple[bool, bool, Dict[str, str], Dict[str, str]]:
        """
        Validate delete entries.

        Args:
            app_info (dict): Application Info dict
            form_data (FormData): Form Data

        Returns:
            Tuple[bool, Dict[str, str], Dict[str, str]]: rc, chgs_detected, errors, new_app_info
        """
        LOGGER.info(f'validate_del_entries() - {len(app_info["_textfiles"])} entries.')
        valid = True
        changes_detected = False
        errors = {}
        new_app_info: dict = app_info.copy()
        textfiles: dict = new_app_info['_textfiles'].copy()
        # Delete entries 1st
        for log_id in app_info['_textfiles'].keys():
            form_fieldname = f'del_{log_id}_check'
            checked = False if form_data.get(form_fieldname) is None else True
            if checked:
                changes_detected = True
                LOGGER.warning(f' - Delete {form_fieldname} / {log_id}')
                textfiles.pop(log_id)
            else:
                LOGGER.info(f' - Leave  {form_fieldname} / {log_id}')        

        if len(textfiles) != len(new_app_info['_textfiles']):
            new_app_info['_textfiles'] = textfiles

        LOGGER.log(f'{"SUCCESS" if valid else "ERROR"}', f'  rc: {valid}, chgs: {changes_detected}, errors: {errors}  entries: {len(new_app_info["_textfiles"])}')
        return valid, changes_detected, errors, new_app_info


    @staticmethod
    def validate_new_entry(id: str, loc: str, app_info: dict) -> Tuple[bool, bool, Dict[str, str], Dict[str, str]]:
        """
        Validate new log entry

        Args:
            id (str): LogID
            loc (str): Log location
            app_info (dict): Application Info dict

        Returns:
            Tuple[bool, Dict[str, str], Dict[str, str]]: rc, chgs_detected, errors, new_app_info
        """
        LOGGER.info(f'validate_new_entry("{id}", "{loc}") - {len(app_info["_textfiles"])} entries.')        
        valid = True
        changes_detected = False
        new_app_info = app_info.copy()
        textfiles: dict = new_app_info['_textfiles'].copy()

        entry: dict = {}
        entry['id']  = ['add_fileid',  id,  id]
        entry['loc'] = ['add_fileloc', loc, id]
        errors: dict = Validation._validate_entry(entry, textfiles)
        if len(errors) > 0:
            valid = False
        elif len(id) > 0:
            changes_detected = True
            textfiles[id] = loc
            new_app_info['_textfiles'] = textfiles
            LOGGER.info(f'- added [{id} / {loc}]')

        LOGGER.log(f'{"SUCCESS" if valid else "ERROR"}', f'  rc: {valid}, chgs: {changes_detected}, errors: {errors} - {len(textfiles)} entries.')
        return valid, changes_detected, errors, new_app_info
    
    @staticmethod
    def _validate_entry(entry_dict: Dict[str, list], textfiles: dict, ignore_existing: bool = False) -> Dict[str, str]:
        """
        Edit a view log entry

        Args:
            entry_dict (Dict[str, list]): {'fieldid': [fieldname, fieldvalue], ...}
            textfiles (dict): List of current log file entries

        Returns:
            Dict[str, str]: errors  {'fieldname': error, ...}
        """
        LOGGER.info(f'  _validate_entry({entry_dict})')
        id_field_name   = entry_dict['id'][0]
        id_field_value  = entry_dict['id'][1]
        loc_field_name  = entry_dict['loc'][0]
        loc_field_value = entry_dict['loc'][1]
        textfile_id     = entry_dict['id'][2]
        
        errors: dict = {}
        if len(id_field_value) > 0 or len(loc_field_value) > 0:
            if len(id_field_value) == 0:
                errors[id_field_name] = 'Must not be an empty string.'
            elif not ignore_existing and textfile_id in textfiles.keys():
                errors[id_field_name] = f'ID [{textfile_id}] must be unique.'

            if len(loc_field_value) == 0:
                errors[loc_field_name] = 'Must not be an empty string.'
            elif not pathlib.Path(loc_field_value).exists():
                errors[loc_field_name] = 'Location does NOT exist.'
        
        if len(errors.keys()) > 0:
            LOGGER.info(f'    errors: {errors}')

        return errors
    
