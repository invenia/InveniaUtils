import copy
import logging
import os

logger = logging.getLogger(__name__)


class Manager(object):
    def __init__(self):
        self.config_dict = {}

    def get_configuration(self, name):
        if not isinstance(name, str):
            raise TypeError("A configuration name must be string")

        if name in self.config_dict:
            config = self.config_dict[name]
        else:
            config = Configuration()
            self.config_dict[name] = config

        return config


class Configuration(object):
    def __init__(self, file_path=None, default_file_path=None):
        """
        Retains the contents of a YAML configuration file for easy access.

        :param file_path: the configuration to load.
        :param default_file_path: a configuration file to fall back on
          when the no file_path is not set.

        The default_file_path behaviour should be abstracted
        outside of the Configuration class.
        """
        self._constants = {}

        self._loaded = False
        self._default_file_path = default_file_path
        self.file_path = file_path

        if file_path:
            self.load(file_path)

    @property
    def constants(self):
        if not self._loaded and self._default_file_path:
            self.load(self._default_file_path, ignore_missing=True)

        return copy.deepcopy(self._constants)

    def load(self, file_path, ignore_missing=False):
        # Avoid loading yaml module at the beginning of this module
        # since this creates an unnecessary requirement when installing
        # the datafeeds package for the first time.
        import yaml

        if ignore_missing and not os.path.isfile(file_path):
            logger.warning("Ignoring missing configuration file: {}".format(file_path))
            return

        with open(file_path, "r") as fp:
            self._constants = yaml.safe_load(fp)
            self._loaded = True

        self.file_path = file_path

    def get_constant(self, path, default=None):
        if not self._loaded and self._default_file_path:
            self.load(self._default_file_path, ignore_missing=True)

        current = self._constants

        for key in path:
            if key in current:
                current = current[key]
            else:
                return default

        if current:
            return copy.deepcopy(current)
        else:
            return default

    def get_file_path(self):
        if self.file_path:
            return self.file_path
        return self._default_file_path


def get_configuration(name):
    return MANAGER.get_configuration(name)


MANAGER = Manager()
