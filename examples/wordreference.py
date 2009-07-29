#!/usr/bin/python
import spynner
import pyquery

browser = spynner.Browser(debug_level=spynner.INFO, html_parser=pyquery.PyQuery)
browser.create_webview()
browser.show()
browser.load("http://www.wordreference.com")
browser.select("#esen")
browser.fill("input[name=enit]", "hola")
browser.click("input[name=b]")
browser.wait_page_load()
browser.soup.make_links_absolute(base_url=browser.url)
print "html:", browser.soup("#Otbl").html()
data = browser.download(browser.soup("img:first").attr('src'))
print "image length:", len(data)
browser.browse()
