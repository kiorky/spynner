import unittest2 as unittest

from spynner.testing import (
    A_SPYNNER_FIXTURE as UNIT_TESTING,
    A_SPYNNER_INTEGRATION_TESTING as INTEGRATION_TESTING,
    A_SPYNNER_FUNCTIONAL_TESTING as FUNCTIONAL_TESTING,
)

from pprint import pprint
from copy import deepcopy as dc

class TestCase(unittest.TestCase):
    """We use this base class for all the tests in this package.
    If necessary, we can put common utility or setup code in here.
    """
    layer = UNIT_TESTING

    def setUp(self):
        super(TestCase, self).setUp()


class IntegrationTestCase(TestCase):
    """Integration base TestCase."""
    layer = INTEGRATION_TESTING


class FunctionalTestCase(TestCase):
    """Functionnal base TestCase."""
    layer = FUNCTIONAL_TESTING

# vim:set ft=python:
