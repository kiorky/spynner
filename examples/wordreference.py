#!/usr/bin/python
import spynner
import pyquery
import os
from StringIO import StringIO

browser = spynner.Browser(debug_level=spynner.INFO)
browser.create_webview()
browser.show()
browser.set_html_parser(pyquery.PyQuery)
browser.load("http://www.wordreference.com")
browser.select("#esen")
browser.fill("input[name=enit]", "hola")
browser.click("input[name=b]")
browser.wait_load()
print "url:", browser.url

# Soup is a PyQuery object
browser.soup.make_links_absolute(base_url=browser.url)
print "html:", browser.soup("#Otbl").html()

# Demonstrate how to download a resource using PyQuery soup
imagedata = browser.download(browser.soup("img:first").attr('src'))
print "image length:", len(imagedata)
browser.close()
