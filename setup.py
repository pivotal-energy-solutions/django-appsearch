# -*- coding: utf-8 -*-
"""setup.py: Django django-company-registration"""

from setuptools import find_packages, setup

setup(name='django-appsearch',
      version='1.0',
      description='Framework and generic app for cross-model searches on a single page',
      author='Tim Vallenta',
      author_email='tvalenta@pivotalenergysolutions.com',
      license='Apache License (2.0)',
      classifiers=[
           'Development Status :: 2 - Pre-Alpha',
           'Environment :: Web Environment',
           'Framework :: Django',
           'Intended Audience :: Developers',
           'License :: OSI Approved :: Apache Software License',
           'Operating System :: OS Independent',
           'Programming Language :: Python',
           'Topic :: Software Development',
      ],
      packages=find_packages(exclude=['tests', 'tests.*']),
      package_data={'appsearch': ['static/js/*.js', 'templates/appsearch/*.html']},
      include_package_data=True,
      requires=['django (>=1.2)'],
)
