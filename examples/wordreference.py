#!/usr/bin/python
import spynner
import pyquery

browser = spynner.Browser(debug_level=spynner.INFO)
browser.create_webview()
browser.show()
browser.load("http://www.wordreference.com")
browser.select("#esen")
browser.fill("input[name=enit]", "hola")
browser.click("input[name=b]")
d = pyquery.PyQuery(browser.html)
d.make_links_absolute(base_url=browser.get_url())
print "html:", d("#Otbl").html()
data = browser.download(d("img:first").attr('src'))
print "image length:", len(data)
browser.browse()
