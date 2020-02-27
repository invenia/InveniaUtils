import unittest
from inveniautils.configuration import Configuration, Manager, get_configuration
from . import full_path


class TestConfigurationObject(unittest.TestCase):
    def test_config_loads(self):
        conf = Configuration(file_path=full_path("test.yaml"))
        self.assertEqual(conf.get_constant(["cred_store", "thingy", "athing"]), "hello")
        self.assertEqual(conf.get_constant(["datafeeds", "another", "thing"]), "boop")
        self.assertEqual(
            conf.get_constant(["raw_store", "why", "rabi"]),
            "Somethings gotta ease your mind",
        )

    def test_config_invalid(self):
        conf = Configuration(file_path=full_path("test.yaml"))
        self.assertIsNone(conf.get_constant(["datafeeds", "invalid"]))
        self.assertIsNone(conf.get_constant(["empty"]))

    def test_config_filepath(self):
        conf = Configuration(file_path=full_path("test.yaml"))
        self.assertEqual(conf.get_file_path(), full_path("test.yaml"))

    def test_config_autoload_default(self):
        c0 = Configuration(default_file_path=full_path("test.yaml"))
        c1 = Configuration(default_file_path=full_path("test.yaml"))
        c2 = Configuration(default_file_path=full_path("test.yaml"))

        self.assertIsNotNone(c0.constants)
        self.assertIsNotNone(c1.get_constant(["datafeeds", "another", "thing"]))
        self.assertEqual(c2.get_file_path(), full_path("test.yaml"))


class TestManagerObject(unittest.TestCase):
    def test_manager_get(self):
        man = Manager()
        c0 = man.get_configuration("test")
        c0.load(full_path("test.yaml"))
        c1 = man.get_configuration("different")

        self.assertNotEqual(c0, c1)
        self.assertEqual(c0, man.get_configuration("test"))
        self.assertEqual(
            c0.get_constant(["raw_store", "why", "rabi"]),
            "Somethings gotta ease your mind",
        )

        c1.load("iNvAlId", True)

    def test_global_manager(self):
        c0 = get_configuration("test")
        c0.load(full_path("test.yaml"))
        c1 = get_configuration("different")

        self.assertNotEqual(c0, c1)
        self.assertEqual(c0, get_configuration("test"))
        self.assertEqual(
            c0.get_constant(["raw_store", "why", "rabi"]),
            "Somethings gotta ease your mind",
        )
