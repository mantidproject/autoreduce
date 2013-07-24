#!/bin/bash

tar -czf ~/rpmbuild/SOURCES/autoreduce.tgz ./autoreduce
rpmbuild -ba ./SPECS/autoreduce.spec
tar -czf ~/rpmbuild/SOURCES/autoreduce-mq.tgz ./autoreduce-mq
rpmbuild -ba ./SPECS/autoreduce-mq.spec
tar -czf ~/rpmbuild/SOURCES/autoreduce-remote.tgz ./autoreduce-remote
rpmbuild -ba ./SPECS/autoreduce-remote.spec
