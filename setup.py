#!/usr/bin/python
#
# Copyright (c) Arnau Sanchez <tokland@gmail.com>

# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>
from setuptools import setup, find_packages
import os
from distutils.cmd import Command

version = '2.4'
url = "https://github.com/makinacorpus/spynner"

def read(rnames):
    setupdir =  os.path.dirname( os.path.abspath(__file__))
    return open(
        os.path.join(setupdir, rnames)
    ).read()

setup(
    name="spynner",
    version=version,
    description="Programmatic web browsing module with AJAX support for Python",
    author="Arnau Sanchez, Mathieu Le Marec-Pasquet",
    author_email="tokland@gmail.com, kiorky@cryptelium.net",
    url=url,
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    install_requires=['BeautifulSoup', 'pyquery'],
    scripts=[],
    license="GPL v3.0",
    long_description = (
        read('README.rst')
        + '\n' +
        read('src/spynner/tests/spynner.rst')
        + '\n' +
        read('CHANGES.rst')
        + '\n'
    ),
    include_package_data=True,
    extras_require = {
        'test': ['ipython', 'plone.testing']
    }, 
    data_files = [
        ('share/doc/spynner/examples',
            ('examples/anothergoogle.py',)),
        #('share/spynner/javascript',
        #    ('src/spynner/javascript/jquery.min.js',
        #     'src/spynner/javascript/jquery.simulate.js')),
    ],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
