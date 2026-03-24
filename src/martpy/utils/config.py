
"""
Configuration module for martpy.
Handles persistent user settings.
"""

import os, shutil
import configparser
from pathlib import Path
from platform import uname


CONFIG_DIR = Path(os.path.expanduser("~"))
CONFIG_FILE = CONFIG_DIR / ".martpyrc"

DEFAULTS = {
    'general': {
        'lang': 'fr'
    }
}


def _get_descr_field(lang='fr'):
    _descr_field = 'descr'
    if not lang == 'fr':
        _descr_field += '_en'
    return _descr_field


class Configuration:
    _instance = None

    # avoid creating a new object for each call - use skeleton
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Configuration, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        self.config = configparser.ConfigParser()
        self.config.read_dict(DEFAULTS)
        if CONFIG_FILE.exists():
            self.config.read(CONFIG_FILE)

    def save(self):
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            self.config.write(f)

    def get(self, section, option):
        return self.config.get(section, option)

    def set(self, section, option, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, str(value))
        self.save()


# Global functions to access configuration easily
def get_config():
    return Configuration()

def get_lang():
    """ Get current language setting ('fr' or 'en') """
    return get_config().get('general', 'lang')

def set_lang(lang):
    """ Set language setting

    Parameters
    ----------
    lang : str
        'fr' for French, 'en' for English
    """
    if lang not in ['fr', 'en']:
        raise ValueError("Language must be 'fr' or 'en'")
    get_config().set('general', 'lang', lang)


def _get_martbin(bin='marthe'):
    """
    Function to retrieve the path to the MART binary.
    This function can be modified to change the path as needed.
    """
    if uname().system == 'Windows':
        martbin = os.path.join(os.environ.get('Bin_Marthe'), '{}.exe'.format(bin))
        if martbin is None or not os.path.exists(martbin):
            raise FileNotFoundError(f"MART binary not found at {martbin}")
    else:
        martbin = shutil.which(bin)
        if not martbin:
            raise FileNotFoundError("MART binary not found in PATH")
    return martbin
