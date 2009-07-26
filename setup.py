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
from distutils.core import setup
from distutils.cmd import Command

version = "0.0.1"

setup(
    name="spynner",
    version=version,
    description="Programmatic web browsing module with AJAX support for Python",
    author="Arnau Sanchez",
    author_email="tokland@gmail.com",
    url="http://code.google.com/p/spynner",
    packages=[  
        "spynner",
    ],
    #install_requires=['pyqt'],
    scripts=[],
    license="GNU Public License v3.0",
    long_description="""
Spynner is a programmatic web browser module for Python with
Javascript/AJAX support. It is based upon the QtWebKit framework.""",
    data_files = [
        ('share/doc/spynner/examples',
            ('examples/wordreference.py',)),
        ('share/spynner/javascript',
            ('javascript/jquery.min.js',
             'javascript/jquery.simulate.js')),
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
