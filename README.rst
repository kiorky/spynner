Intro
=====================

.. contents::

Spynner is a stateful programmatic web browser module for Python. It is based upon `PyQT <http://www.qtsoftware.com/>`_ and `WebKit <http://webkit.org/>`_, so it supports Javascript, AJAX, and every other technology that !WebKit is able to handle (Flash, SVG, ...). Spynner takes advantage of `JQuery <http://jquery.com>`_. a powerful Javascript library that makes the interaction with pages and event simulation really easy.

Using Spynner you would able to simulate a web browser with no GUI (though a browsing window can be opened for debugging purposes), so it may be used to implement crawlers or acceptance testing tools.

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

API
=====
http://tokland.freehostia.com/googlecode/spynner/api/

You can generate the API locally (will create docs/api directory)::

    python setup.py gen_doc

Usage
=========
A basic example::

    import spynner
    browser = spynner.Browser()
    browser.load("http://www.wordreference.com")
    browser.runjs("console.log('I can run Javascript')")
    browser.runjs("console.log('I can run jQuery: ' + jQuery('a:first').attr('href'))")
    browser.select("#esen")
    browser.wk_fill("input[name=enit]", "hola")
    browser.click("input[name=b]")
    browser.wait_load()
    print browser.url, browser.html
    browser.close()

Sometimes you'll want to see what is going on::

    browser = spynner.Browser()
    browser.debug_level = spynner.DEBUG
    browser.create_webview()
    browser.show()

See more examples in the repository: https://github.com/kiorky/spynner/tree/master/examples

Interact with the controls
============================
- See the implementation docstrings or examples !
- You have three levels of control:

  - webkit methods which are recommended to us (wk_fill_*, wk_click_*) which are jquery based
  - classical methods (fill, click_*) which are jquery based
  - low level using QT raw events which are not that well  working ATM.
    At least, you can move the mouse

Running Javascript
====================
Spynner uses jQuery to make Javascript interface easier.
By default, two modules are injected to every loaded page:

  * `JQuery core <http://docs.jquery.com/Downloading_jQuery>`_ Amongst other things, it adds the powerful `JQuery selectors <http://docs.jquery.com/Selectors>`_, which are used internally by some Spynner methods.
    Of course you can also use jQuery when you inject your own code into a page.

  * `Simulate <http://code.google.com/p/jqueryjs/source/browse/trunk/plugins/simulate>`_ jQuery plugin: Makes it possible to simulate mouse and keyboard events (for now spynner uses it only in the _click_ action). Look up the library code to see which kind of events you can fire.

Note that you must use __jQuery(...)_ instead of _jQuery(...)_  or the common shortcut _$(...)_.
That prevents name clashing with the jQuery library used by the page.

Cook your soup: parsing the HTML
===================================
You can parse the HTML of a webpage with your favorite parsing library `BeautifulSoup <http://www.crummy.com/software/BeautifulSoup>`_, `lxml <http://codespeak.net/lxml/>`_ ,..
Since we are already using Jquery for Javascript, it feels just natural to work with `pyquery <http://pypi.python.org/pypi/pyquery>`_, its Python counterpart::

    import spynner
    import pyquery
    browser = spynner.Browser()
    ...
    d = pyquery.Pyquery(browser.html)
    d.make_links_absolute(browser.get_url())
    href = d("#somelink").attr("href")
    browser.download(href, open("/path/outputfile", "w"))

Running Spynner without X11
====================================
- Spynner needs a X11 server to run. If you are running it in a server without X11 you must install the virtual `Xvfb server <http://en.wikipedia.org/wiki/Xvfb>`_.
  Debian users can use the small wrapper (xvfb-run). If you are not using Debian, you can download it here:
  http://www.mail-archive.com/debian-x@lists.debian.org/msg69632/x-run ::

    xvfb-run python myscript_using_spynner.py

- You can also use tightvnc.

