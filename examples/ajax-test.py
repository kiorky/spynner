#!/usr/bin/python
import spynner
  
browser = spynner.Browser()
browser.create_webview(True)
browser.load("http://juicystudio.com/experiments/ajax/index.php")
browser.click_ajax("#fact")
print browser.runjs("_jQuery('#update').html()").toString()
browser.click_ajax("#fact")
print browser.runjs("_jQuery('#update').html()").toString()
browser.close()
