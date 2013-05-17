#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'
import spynner
import os
import sys

class test(object):
    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31"
    proxyg = os.environ.get('SPY_PROXY', None)
    proxyd = os.environ.get('SPYD_PROXY', None)
    img = 'https://www.google.fr/images/srpr/logo4w.png'
    url = 'https://www.google.fr'

    def test(self):
        IMG = self.img
        URL = self.url
        assert self.proxyg is not None, "no global proxy set"
        assert self.proxyd is not None, "no download proxy set"
        br = self.browser = spynner.Browser(
            ignore_ssl_errors=False,
            user_agent=self.user_agent,
            debug_level=spynner.WARNING,
            debug_stream=sys.stderr)
        br.show()
        data, content = {}, {}
        # no proxy
        data['noproxy'] = br.download(IMG)
        br.load(URL, None)
        content['noproxy'] = br.html
        # no proxy - alt1
        br.set_proxy("")
        data["proxy_void"] = br.download(IMG)
        br.load(URL, None)
        content["proxy_void"] = br.html
        # no proxy - alt2
        br.set_proxy(None)
        data["proxy_none"] = br.download(IMG)
        br.load(URL, None)
        content["proxy_none"] = br.html
        # global proxy
        br.set_proxy(self.proxyg)
        data["proxy_g"] = br.download(IMG)
        br.load(URL, None)
        content["proxy_g"] = br.html
        # use a proxy only @ download level
        br.load(URL)
        data["proxy_d"] = br.download(IMG, proxy_url=self.proxyd)
        for i in data:
            if data["noproxy"] != data[i]:
                raise Exception("Download failed for %s" % i)

def main():
    test().test()


"""
run with
SPY_PROXY="http://foo" SPYD_PROXY="http://bar" $PYTHON examples/googleproxy.py
"""


if __name__ == '__main__':
    main()

# vim:set et sts=4 ts=4 tw=80:
