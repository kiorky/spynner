#!/usr/bin/env bash
ps aux|grep -- 'bin/buildout'|awk '{print $2}'|xargs kill -9
bin/buildout  $@
