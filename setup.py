#!/usr/bin/python
from setuptools import setup


setup(
    setup_requires=['pbr==5.9.0'],
    pbr=True,
    platforms=['any'],
    zip_safe=False,
    test_suite='bug_crowd.test',
)
