Intro
=====================

.. contents::

Spynner is a stateful programmatic web browser module for Python.
It is based upon `PyQT <http://www.qtsoftware.com/>`_ and `WebKit <http://webkit.org/>`_.
It supports Javascript, AJAX, and every other technology that !WebKit is able to handle (Flash, SVG, ...).
Spynner takes advantage of `JQuery <http://jquery.com>`_. a powerful Javascript library that makes the interaction with pages and event simulation really easy.

Using Spynner you would able to simulate a web browser with no GUI (though a browsing window can be opened for debugging purposes), so it may be used to implement crawlers or acceptance testing tools.


See usage on: https://github.com/makinacorpus/spynner/tree/master/src/spynner/tests/spynner.rst
Or below if the section is preset

Credits
========
Companies
---------
|makinacom|_

  * `Planet Makina Corpus <http://www.makina-corpus.org>`_
  * `Contact us <mailto:python@makina-corpus.org>`_

.. |makinacom| image:: http://depot.makina-corpus.org/public/logo.gif
.. _makinacom:  http://www.makina-corpus.com

Authors
------------

- Mathieu Le Marec - Pasquet <kiorky@cryptelium.net>
- Arnau Sanchez <tokland@gmail.com>

Contributors
-----------------

- Leo Lou <https://github.com/l4u>

Dependencies
===================

  * `Python >=26 <http://www.python.org>`_
  * `PyQt > 443 <http://www.riverbankcomputing.co.uk/software/pyqt/download>`_
  * Libxml2 / Libxslt libraries and includes files for lxml

Feedback
==============
Open an `Issue <https://github.com/kiorky/spynner/issues>`_ to report a bug or request a new feature. Other comments and suggestions can be directly emailed to the authors_.

Install
============
* Throught regular easy_install / buildout::

    easy_install spynner

* The bleeding edge version is hosted on github::

    git clone https://github.com/makinacorpus/spynner.git
    cd spynner
    python setup.py install

Running Spynner without X11
====================================
- Spynner needs a X11 server to run. If you are running it in a server without X11.
  You must install the virtual `Xvfb server <http://en.wikipedia.org/wiki/Xvfb>`_.
  Debian users can use the small wrapper (xvfb-run). If you are not using Debian, you can download it here:
  http://www.mail-archive.com/debian-x@lists.debian.org/msg69632/x-run ::

    xvfb-run python myscript_using_spynner.py

- You can also use tightvnc, which is the solution of the actual maintainer [kiorky].

