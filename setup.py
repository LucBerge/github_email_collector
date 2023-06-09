# coding: utf8

import sys
import setuptools

with open('requirements.txt', 'r') as f:
    requirements = [
        s for s in [
            line.split('#', 1)[0].strip(' \t\n') for line in f
        ] if s != ''
    ]

long_description = open("README.md", "r").read()

setuptools.setup(
    name='github_email_collector',
    version='0.2',
    author='LucBerge',
    author_email='lucas.bergeron@outlook.fr',
    description="Collect email address of users affiliated to a given repository",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/LucBerge/github_email_collector',
    packages=setuptools.find_packages(),
    install_requires=requirements
)
