# -*- coding: utf-8 -*-
"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

__name__ = "appsearch"
__author__ = "Pivotal Energy Solutions"
__version_info__ = (2, 1, 26)
__version__ = "2.1.26"
__date__ = "2014/07/22 4:47:00 PM"

__credits__ = ["Tim Valenta", "Steven Klass"]
__license__ = "See the file LICENSE.txt for licensing information."

from codecs import open
from os import path

# Always prefer setuptools over distutils
from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))
base_url = "https://github.com/pivotal-energy-solutions/django-appsearch/"

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="django-appsearch",
    zip_safe=False,  # eggs are the devil.
    version="2.1.26",
    description="Framework and generic app for cross-model searches on a single page",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="django search",
    author=__author__,
    author_email="steve@homerecord.com",
    url=base_url,
    download_url="{0}/archive/{1}.tar.gz".format(base_url, __version__),
    packages=find_packages(exclude=["docs", "appsearch/tests"]),
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Utilities",
    ],
    python_requires=">=3.9",
    install_requires=["django>=3.2", "python-dateutil", "six"],
    scripts=[],
    project_urls={
        "Bug Reports": "{}/issues".format(base_url),
        "Source": base_url,
    },
)
