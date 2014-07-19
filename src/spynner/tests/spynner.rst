Initializing the browser
==================================
The main concept to have a browser out there::

    >>> import spynner, os, sys
    >>> def print_contents(browser, dest='~/.browser.html'):
    ...     """Print the browser contents somewhere for you to see its context
    ...     in doctest pdb, type print_contents(browser) and that's it, open firefox
    ...     with file://~/browser.html."""
    ...     import os
    ...     open(os.path.expanduser(dest), 'w').write(browser.contents)
    >>> import time
    >>> from StringIO import StringIO
    >>> debug_stream = StringIO()
    >>> bp = os.path.dirname(spynner.tests.__file__)

The browser::

    >>> browser = spynner.Browser(debug_level=spynner.DEBUG, debug_stream=debug_stream)

When all is done::

    >>> browser.close()
    >>> def run_debug(callback, *args, **kwargs): # ** *
    ...     pos = debug_stream.pos
    ...     ret = callback(*args, **kwargs)
    ...     show_debug(pos)
    ...     return ret


    >>> def show_debug(pos=None):
    ...     if not pos: print debug_stream.getvalue()
    ...     else:
    ...         pnow = debug_stream.pos
    ...         debug_stream.seek(pos)
    ...         print debug_stream.read()
    ...         debug_stream.seek(pnow)


Debugging
==========
Spynner uses webkit which is somewhat low level, never hesitate to activate verbose logs
Sometimes you'll want to see what is going on::

    >>> browser = spynner.Browser(debug_level=spynner.DEBUG, debug_stream=debug_stream)

Or after initialization::

    >>> browser.debug_level = spynner.DEBUG

See more examples in the repository: https://github.com/kiorky/spynner/tree/master/examples

Showing spynner window
========================
Maybe, you also want to have an output of what the browser is doing, just use that::

    >>> browser.show()

You can hide the webview with::

    thebrowser.hide()


Running Javascript
====================

Simply use::

    >>> ret = browser.runjs('console.log("foobar")')

Browsing with spynner
============================
A basic but complicated example
Word reference has resources loading which can fails, for thus we wait on the content to be there.

If the website was good, we could simple use ::

    >>> ret = debug_stream.read()
    >>> browser.load(bp+"/html_controls.html")
    True

This method throws an exception on timeout, and can customize the default 30 seconds timeout.

But there, our target can randomly fails.
Instead, we will load and wait for something in the DOM to be there to continue.
We wait to have 'aaa' in the html, thus with unlimited tries at 1 seconds intervals each
::

    >>> def wait_load(br):
    ...     return  'aaa' in browser.html

Hit the wrong url, Eck, you are on an unlimited loop !::

    >>> browser.load(bp+"html_controls.html", 1, wait_callback=wait_load)

    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    content loaded, waiting for content to mach the callback
    <Control-C>

Hit the wrong url, Eck, you are on an unlimited loop unless you wear condoms and set the tries!
It will throw an exception, but stop::

    >>> ret = debug_stream.read()

    Traceback (most recent call last):
      ...
    SpynnerTimeout: SPYNNER waitload: Timeout reached: 2 retries for 1s delay.

Finnish to play, go to the real target::

    >>> ret = browser.load(bp+"/html_controls.html", 1, wait_callback=wait_load)
    >>> [a for a in debug_stream.getvalue().splitlines() if 'SPYNNER waitload' in a][-1]
    'SPYNNER waitload: The callback found what it was waiting for in its contents!'

Interact with the controls
============================
- See the implementation docstrings or examples !
- You have three levels of control:

  - webkit methods which are recommended to us (wk_fill_*, wk_click_*) which are jquery based. The fill_* and click_*
  - The classical methods (fill, click_*) are now wrappers to the wk_* methods.
  - low level using QT raw events which are not that well working ATM.
    At least, you can move the mouse and sendKeys but it's a case per case coding.

Setup::

    >>> browser.close()
    >>> del browser

Using radio inputs
----------------------
::

    >>> browser = spynner.Browser(debug_level=spynner.DEBUG, debug_stream=debug_stream)
    >>> ret = browser.load(bp+'/html_controls.html', 1, wait_callback=wait_load)


Using jquery
++++++++++++++++++
::

   >>> browser.load_jquery(True)

   >>> browser.radio('#radiomea')

    >>> ret = run_debug(browser.runjs, '$("input[name=radiome]").each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.val()+" "+je.attr("checked"));});')
    Run Javascript code: $("input[name=radiome]").each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.val()+" "+je.attr("checked"));});
    Javascript console (:1): radiomea a true
    Javascript console (:1): radiomeb b false
    Javascript console (:1): radiomec c false
    <BLANKLINE>
    >>> browser.radio('#radiomeb')
    >>> ret = run_debug(browser.runjs, '$("input[name=radiome]").each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.val()+" "+je.attr("checked"));});')
    Run Javascript code: $("input[name=radiome]").each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.val()+" "+je.attr("checked"));});
    Javascript console (:1): radiomea a false
    Javascript console (:1): radiomeb b true
    Javascript console (:1): radiomec c false
    <BLANKLINE>


Using webkit native methods
+++++++++++++++++++++++++++++
Under the hood, we use this.evaluateJavaScript('this.value = xxx') ::

    >>> browser.wk_radio('#radiomea')
    >>> browser.load_jquery(True)
    >>> ret = run_debug(browser.runjs, '$("input[name=radiome]").each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.val()+" "+je.attr("checked"));});')
    Run Javascript code: $("input[name=radiome]").each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.val()+" "+je.attr("checked"));});
    Javascript console (:1): radiomea a true
    Javascript console (:1): radiomeb b false
    Javascript console (:1): radiomec c false
    <BLANKLINE>


Using check inputs
----------------------
Using webkit native methods
+++++++++++++++++++++++++++++
::

    >>> browser.close()
    >>> browser = spynner.Browser(debug_level=spynner.DEBUG, debug_stream=debug_stream)
    >>> ret = browser.load(bp+'/html_controls.html', 1, wait_callback=wait_load)
    >>> ret = browser.load_jquery(True)

Under the hood, we use this.evaluateJavaScript('this.value = xxx') ::

    >>> browser.wk_check('#checkmea')
    >>> ret = run_debug(browser.runjs, '$($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});')
    Run Javascript code: $($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});
    Javascript console (:1): checkmea true
    Javascript console (:1): checkmeb false
    Javascript console (:1): checkmec false
    <BLANKLINE>
    >>> browser.wk_check(['#checkmeb', '#checkmec'])
    >>> ret = run_debug(browser.runjs, '$($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});')
    Run Javascript code: $($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});
    Javascript console (:1): checkmea true
    Javascript console (:1): checkmeb true
    Javascript console (:1): checkmec true
    <BLANKLINE>
    >>> browser.wk_uncheck(['#checkmeb', '#checkmec'])
    >>> ret = run_debug(browser.runjs, '$($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});')
    Run Javascript code: $($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});
    Javascript console (:1): checkmea true
    Javascript console (:1): checkmeb false
    Javascript console (:1): checkmec false
    <BLANKLINE>
    >>> browser.wk_uncheck(['#checkmea'])
    >>> ret = run_debug(browser.runjs, '$($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});')
    Run Javascript code: $($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});
    Javascript console (:1): checkmea false
    Javascript console (:1): checkmeb false
    Javascript console (:1): checkmec false
    <BLANKLINE>

Using jquery
+++++++++++++++++++
::

    >>> browser.load(bp+'/html_controls.html', 1, wait_callback=wait_load)
    >>> browser.load_jquery(True)

Under the hood, we use $(sel).attr('checked', 'checked')::

    >>> browser.check('#checkmea')
    >>> ret = run_debug(browser.runjs, '$($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});')
    Run Javascript code: $($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});
    Javascript console (:1): checkmea true
    Javascript console (:1): checkmeb false
    Javascript console (:1): checkmec false
    <BLANKLINE>
    >>> browser.check(['#checkmeb', '#checkmec'])
    >>> ret = run_debug(browser.runjs, '$($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});')
    Run Javascript code: $($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});
    Javascript console (:1): checkmea true
    Javascript console (:1): checkmeb true
    Javascript console (:1): checkmec true
    <BLANKLINE>
    >>> browser.uncheck(['#checkmeb', '#checkmec'])
    >>> ret = run_debug(browser.runjs, '$($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});')
    Run Javascript code: $($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});
    Javascript console (:1): checkmea true
    Javascript console (:1): checkmeb false
    Javascript console (:1): checkmec false
    <BLANKLINE>
    >>> browser.uncheck(['#checkmea'])
    >>> ret = run_debug(browser.runjs, '$($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});')
    Run Javascript code: $($("input[name=checkme]")).each(function(i, e){je=$(e);console.log(je.attr("id")+" "+je.attr("checked"));});
    Javascript console (:1): checkmea false
    Javascript console (:1): checkmeb false
    Javascript console (:1): checkmec false
    <BLANKLINE>

Using select inputs
----------------------
Using webkit native methods
+++++++++++++++++++++++++++++
::

    >>> ret = browser.load(bp+'/html_controls.html', 1, wait_callback=wait_load)
    >>> ret = browser.load_jquery(True)

Under the hood, we use this.evaluateJavaScript('this.value = xxx') ::

    >>> browser.wk_select('#sel', 'aa')
    >>> browser.runjs('$("#sel").val();').toString()
    PyQt4.QtCore.QString(u'aa')
    >>> browser.wk_select('#sel', 'bb')
    >>> browser.runjs('$("#sel").val();').toString()
    PyQt4.QtCore.QString(u'bb')
    >>> browser.wk_select('#sel', 'dd')
    >>> browser.runjs('$("#sel").val();').toString()
    PyQt4.QtCore.QString(u'dd')

If it is not a multiple it takes the last::

    >>> browser.wk_select('#sel', ['aa', 'bb', 'dd'])
    >>> browser.runjs('$("#sel").val();').toString()
    PyQt4.QtCore.QString(u'dd')

If it is a multiple it takes all::

    >>> browser.wk_select('#msel', ['maa', 'mbb', 'mdd'])
    >>> ret = run_debug(browser.runjs, '$($("#msel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});')
    Run Javascript code: $($("#msel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});
    Javascript console (:1): maaa true
    Javascript console (:1): mbbb true
    Javascript console (:1): mccc false
    Javascript console (:1): mddd true
    <BLANKLINE>

Using jquery
+++++++++++++++++++
::

    >>> browser.load(bp+'/html_controls.html', 1, wait_callback=wait_load)
    >>> browser.load_jquery(True)

Under the hood, we use $(sel).attr("selected", "selected")::

    >>> browser.select('#sel option[name="bbb"]')
    >>> pos = debug_stream.pos
    >>> ret = run_debug(browser.runjs, '$($("#sel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});')
    Run Javascript code: $($("#sel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});
    Javascript console (:1): aaa false
    Javascript console (:1): bbb true
    Javascript console (:1): ccc false
    Javascript console (:1): ddd false
    <BLANKLINE>

With a select with multiple args, it can also not deselect already selected values (remove as default)::

    >>> browser.select('#asel option[name="bbb"]', remove=False)
    >>> ret = run_debug(browser.runjs, '$($("#asel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});')
    Run Javascript code: $($("#asel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});
    Javascript console (:1): aaa false
    Javascript console (:1): bbb true
    Javascript console (:1): ccc true
    Javascript console (:1): ddd false
    <BLANKLINE>
    >>> browser.select('#asel option[name="bbb"]', remove=True)
    >>> ret = run_debug(browser.runjs, '$($("#asel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});')
    Run Javascript code: $($("#asel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});
    Javascript console (:1): aaa false
    Javascript console (:1): bbb true
    Javascript console (:1): ccc false
    Javascript console (:1): ddd false
    <BLANKLINE>

If it is a multiple it takes all::

    >>> browser.select(['#msel option[name="mbbb"]', '#msel option[name="mddd"]'])
    >>> ret = run_debug(browser.runjs, '$($("#msel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});')
    Run Javascript code: $($("#msel option")).each(function(i, e){je=$(e);console.log(je.attr("name")+" "+je.attr("selected"));});
    Javascript console (:1): maaa false
    Javascript console (:1): mbbb true
    Javascript console (:1): mccc false
    Javascript console (:1): mddd true
    <BLANKLINE>


Using text inputs
----------------------
Using webkit native methods
+++++++++++++++++++++++++++++
Under the hood, we use this.evaluateJavaScript('this.value = xxx')::

    >>> browser.wk_fill('input[name=w]', 'bar')

Using jquery
+++++++++++++++++++
Under the hood, we use jQuery(selector).val(xxx)::

    >>> browser.fill('input[name="w"]', 'foo')
    >>> ret = run_debug(browser.fill, 'input[name="w"]', 'foo')
    Run Javascript code: $('input[name="w"]').val('foo')
    <BLANKLINE>

Jquery Notes
=============
Spynner uses jQuery to make Javascript interface easier.
By default, two modules are injected to every loaded page:

  * `JQuery core <http://docs.jquery.com/Downloading_jQuery>`_ Amongst other things, it adds the powerful `JQuery selectors <http://docs.jquery.com/Selectors>`_, which are used internally by some Spynner methods.
    Of course you can also use jQuery when you inject your own code into a page.


  * [OBSOLETE, USE AT YOU OWN RISK, NO MAINTAINED, NO BUGFIX DONE] `Simulate <http://code.google.com/p/jqueryjs/source/browse/trunk/plugins/simulate>`_ jQuery plugin: Makes it possible to simulate mouse and keyboard events (for now spynner uses it only in the _click_ action). Look up the library code to see which kind of events you can fire.


AS nowodays jquery is already included on major websites, so we must not inject if the javascript is already loaded by the targeted website.

Browser jquery constructor related switches
-------------------------------------------
Thus if you are targeting a website without jquery just use::

    Browser(embed_jquery=True)

By default the variable using jquery is "$", if your website is using something different use::

    Browser(jslib="jQueryObjectVarName")

Where in javascript jQuery is referenced by::

    JAVASCRIPT:: """ jQueryObjectVarName("div") """

If you need jquery compatibility layer (jQuery.noConflict()), the variable referencing jquery will be "spynnerjq", use ::

    Browser(want_compat=True)


Loading manually jquery
--------------------------
::

    >>> time.sleep(3)
    >>> browser.close()
    >>> browser = spynner.Browser(debug_level=spynner.DEBUG, debug_stream=debug_stream)
    >>> browser.show()
    >>> ret = run_debug(browser.runjs,"console.log(typeof(jQuery));")
    Run Javascript code: console.log(typeof(jQuery));
    Javascript console (:1): undefined
    <BLANKLINE>

Eck, we didnt included jQuery !
 loading it::

    >>> ret = browser.load_jquery(force=True)
    >>> ret = run_debug(browser.runjs, "console.log(typeof(jQuery));")
    Run Javascript code: console.log(typeof(jQuery));
    Javascript console (:1): function
    <BLANKLINE>

Cook your soup: parsing the HTML
===================================
You can parse the HTML of a webpage with your favorite parsing library eg: `BeautifulSoup <http://www.crummy.com/software/BeautifulSoup>`_, `lxml <http://codespeak.net/lxml/>`_ , or lxml, or ...
Since we are already using Jquery for Javascript.
It feels just natural to work with `pyquery <http://pypi.python.org/pypi/pyquery>`_, its Python counterpart::

    >>> import pyquery
    >>> ret = browser.load(bp+'/html_controls.html')
    >>> d = pyquery.PyQuery(browser.html)
    >>> aaa = d.make_links_absolute("http://foo")[0]
    >>> [dict(a.items())['href'] for a in  d.root.xpath('//a')]
    ['http://foo/foo', 'http://foo/a/foo', 'http://foo/../b/foo', 'http://foo/c/foo', 'http://foo/d/foo']


HTTP Headers
============
You can give a list of http headers to send either which each request at
construct time or via the load methods

Headers are in the form:

    - (['User-Agent', 'foobar')]

SSL support
=============

you have two keywords argument to specify:

    - a list (see QtSsl) of supported ciphers to use
    - the protocol to use (sslv2, tlsv1, sslv)3)

Mouse
========
you can move the move on a css selector ::

    br.move_mouse('.myclass', [offsetx=0, offsety=0])

Proxy support
=============
Spynner support all proxiess supported by qt (http(s), socks5 & ftp)

See **examples/proxy.py** in the examples directory

basically use::

    br.set_proxy('foo:3128')
    br.set_proxy('http://foo:3128')
    br.set_proxy('http://user:suserpassword@foo:3128')
    br.set_proxy('https://user:suserpassword@foo:3128')
    br.set_proxy('socks5://user:suserpassword@foo:3128')
    br.set_proxy('httpcaching://user:suserpassword@foo:3128')
    br.set_proxy('ftpcaching://user:suserpassword@foo:3128')

You can also use proxy in the download method.
Note that it will use by default the proxy setted via a previous br.set_proxy call::

    br.download('http://superfile', proxy_url='foo:3128')


