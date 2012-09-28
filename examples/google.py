#!/usr/bin/python
import spynner
import pyquery

browser = spynner.Browser(debug_level=spynner.INFO)
browser.create_webview()
browser.show()
browser.load("http://www.wordreference.com")
browser.load_jquery(True)
browser.choose("input[name=lr=lang_es]")
browser.click("input[name=enit]")
browser.click("a[class=l]:first")
d = pyquery.PyQuery(browser.html)
d.make_links_absolute(base_url=browser.url)
href = d('a:last').attr('href')
print href
print len(browser.download(href))
browser.browse()
