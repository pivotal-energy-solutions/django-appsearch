# -*- coding: utf-8 -*-
"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from codecs import open
from os import path

# Always prefer setuptools over distutils
from setuptools import find_packages, setup

from appsearch import __version__, __author__

here = path.abspath(path.dirname(__file__))
base_url = 'https://github.com/pivotal-energy-solutions/django-appsearch/'

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='django-appsearch',
      zip_safe=False,  # eggs are the devil.
      version=__version__,
      description='Framework and generic app for cross-model searches on a single page',
      long_description=long_description,
      long_description_content_type='text/markdown',
      keywords='django search',
      author=__author__,
      author_email='steve@homerecord.com',
      url=base_url,
      download_url='{0}/archive/{1}.tar.gz'.format(base_url, __version__),
      packages=find_packages(exclude=['docs', 'appsearch/tests']),
      include_package_data=True,
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Environment :: Web Environment',
                   'Framework :: Django',
                   'Framework :: Django :: 2.2',
                   'Framework :: Django :: 3.0',
                   'Framework :: Django :: 3.1',
                   'Framework :: Django :: 3.2',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.8',
                   'Programming Language :: Python :: 3.9',
                   'Programming Language :: Python :: 3.10',
                   'Topic :: Utilities'],
      python_requires='>=3.8.*',
      install_requires=[
          'django>2.2',
          'python-dateutil',
          'six'
      ],
      scripts=[],
      project_urls={
          'Bug Reports': '{}/issues'.format(base_url),
          'Source': base_url,
      })
