CHANGELOG
============
2.16 (unreleased)
-----------------

- Nothing changed yet.


2.15 (2013-07-16)
-----------------

- fix #46


2.14 (2013-06-05)
-----------------

- cookie jar fix (#41)


2.13 (2013-05-17)
-----------------

- Better proxy support
- Travis setup


2.12 (2013-05-03)
-----------------

- Cookie jar fix


2.11 (2013-04-23)
-----------------

- fix release again

2.10 (2013-04-22)
-----------------

- fix release


2.9 (2013-04-22)
----------------

- run natives clicks with autopy


2.8 (2013-04-19)
----------------

- add a helper to move the mouse more easily


2.7 (2013-04-17)
----------------

- Better ssl support
- better http headers support
- pyside support
- better cookie support


2.6 (2013-03-07)
----------------

- fix #17: download timeout


2.5 (2013-03-06)
----------------

- fix #25: new signal api for sslErrors


2.4 (2012-09-28)
----------------

- Example google fixed


2.3 (2012-09-28)
----------------

- documentation


2.2 (2012-09-20)
----------------

- Fix bug where jquery compatiblity mode can be not activated
  thx to yusumishi (yusumishi@gmail.com) for report.


2.1 (2012-08-30)
----------------

- proper release


2.0 (2012-08-05)
----------------

- Make new defaults for sane initialization & api cleanup, now:
        
    - We remapped simulations's functions to wk_* ones
    - we added extensive documentation in src/spynner/tests/spynner.rst
    - we do not embed jquery as default
    - we do not embed jquery's simulate plugins automaticly which is totally deprecated


1.11 (2012-08-04)
-----------------

- proper release


1.10 (2011-06-07)
-----------------

- add wk_check/_unckeck methods


1.9 (2011-05-29)
----------------

- Rework javascript load  [kiorky]
- Some try in native events [kiorky]
- Fix directory issue [kiorky]
- add Samples  [kiorky]
- Fix download cookiesjar free problem [kiorky <kiorky@cryptelium.net>]
- Allow download to be tracked for further reuse [kiorky <kiorky@cryptelium.net>]
- Generate filenames by looking for their filename in response objects. [kiorky <kiorky@cryptelium.net>]
- Add api methods to:

        - send raw keyboard keys
        - send qt raw mouse clicks
        - use qtwebkit native JS click element & fill values
        - some helpers to wait for content

  [kiorky]

- Add download files tracker [kiorky]

0.0.3 (2009-08-01)
------------------
- Click does not wait for page load
- Use QtNetwork infrastructure to download files
- Expose webkit objects in Browser class
- Change jQuery to _jQuery
- HTTP authentication
- Callbacks for Javascript confirm and prompts
- Properties: url, html, soup
- Better docstrings (using epydoc)
- Implement image snapshots
- Implement URL filters
- Implement cookies setting
  [tokland <tokland@gmail.com>]


0.0.2 (2009-07-27)
---------------------
- Use browser.html instead of browser.get_html
- Fix setup.py to make it compatible with Win32
- Add a URL filter mechanism (with a callback)
- Use class-methods instead of burdening Browser.__init__
- Instance variable to ignore SSL certificate errors
- Start using epydoc format for API documentation
- Add create_webview/destroy_webview for GUI debugging
  [tokland <tokland@gmail.com>]

0.0.1 (2009-07-25)
--------------------
- Initial release.  [tokland <tokland@gmail.com>]


.. vim:set sts=4 ts=4 ai et tw=0:
