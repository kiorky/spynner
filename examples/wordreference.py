#!/usr/bin/env python
import spynner
import pyquery

browser = spynner.Browser(debug_level=spynner.DEBUG)
browser.create_webview()
browser.show()
browser.set_html_parser(pyquery.PyQuery)
browser.load("http://www.wordreference.com")
browser.select("#esen")
browser.fill("input[name=w]", "hola")
browser.click("input[name=B10]")
browser.wait_load()
print "url:", browser.url

# Soup is a PyQuery object
browser.soup.make_links_absolute(base_url=browser.url)
print "html:", browser.soup("#Otbl").html()

# Demonstrate how to download a resource using PyQuery soup
imagedata = browser.download(browser.soup("img:first").attr('src'))
print "image length:", len(imagedata)
browser.close()
