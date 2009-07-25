#!/usr/bin/python
import spynner
import pyquery

browser = spynner.Browser(True, verbose_level=spynner.INFO)
browser.show()
browser.load("http://www.google.com")
browser.choose("input[value=lr=lang_es]")
browser.fill("input[name=q]", "archlinux")
browser.click("input[name=btnG]")
browser.click("a[class=l]:first")
html = browser.get_html()
d = pyquery.PyQuery(html)
d.make_links_absolute(base_url=browser.get_url())
href = d('a:last').attr('href')
print href
print len(browser.download(href))
browser.browse()
