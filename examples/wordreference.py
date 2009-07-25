#!/usr/bin/python
import spynner
import pyquery

browser = spynner.Browser(True, verbose_level=spynner.INFO)
browser.show()
browser.load("http://www.wordreference.com")
browser.select("#esen")
browser.fill("input[name=enit]", "hola")
browser.click("input[name=b]")
html = browser.get_html()
d = pyquery.PyQuery(html)
d.make_links_absolute(base_url=browser.get_url())
print "hmlt:", d("#Otbl").html()
data = browser.download(d("img:first").attr('src'))
print "image length:", len(data)
browser.browse()
