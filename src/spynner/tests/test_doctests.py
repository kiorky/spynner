"""
Launching all doctests in the tests directory using:

    - the base layer in testing.py

"""

from spynner.tests.base import FunctionalTestCase

# GLOBALS avalaible in doctests
# IMPORT/DEFINE objects there or inside ./user_globals.py (better)
# globals from the testing product are also available.
# example:
# from for import bar
# and in your doctests, you can do:
# >>> bar.something
from spynner.tests.globals import *
from spynner.testing import A_SPYNNER_FUNCTIONAL_TESTING as FUNCTIONAL_TESTING


import unittest2 as unittest
import glob
import os
import logging
import doctest
from plone.testing import layered

optionflags = (doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE| doctest.REPORT_ONLY_FIRST_FAILURE)

def test_suite():
    """."""
    logger = logging.getLogger('spynner')
    cwd = os.path.dirname(__file__)
    files = []
    try:
        files = glob.glob(os.path.join(cwd, '*txt'))
        files += glob.glob(os.path.join(cwd, '*rst'))
    except Exception,e:
        logger.warn('No doctests for spynner')
    suite = unittest.TestSuite()
    globs = globals()
    for s in files:
        suite.addTests([
            layered(
                doctest.DocFileSuite(
                    s,
                    globs = globs,
                    module_relative=False,
                    optionflags=optionflags,
                ),
                layer=FUNCTIONAL_TESTING
            ),
        ])
    return suite


