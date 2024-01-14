import re
from setuptools import setup

version = ''
with open('./disstat/__init__.py') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)


setup(name='disstat.py',
      version=version,
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      license='Apache License 2.0',
      packages=['disstat'],
      install_requires=["aiohttp",
                        "psutil",
                        "setuptools",
                        "discord"],
      include_package_data=True,
      author='The DT',
      url='https://github.com/thedtvn/disstat.py',
      description='disstat.py is a python library for DisStat'
      )
