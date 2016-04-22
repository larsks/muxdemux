from setuptools import setup, find_packages
from muxdemux import __version__

with open('requirements.txt') as fd:
    requires = fd.read().splitlines()

setup(name='muxdemux',
      author='Lars Kellogg-Stedman',
      author_email='lars@oddbit.com',
      url='https://github.com/larsks/muxdemux',
      version=__version__,
      packages=find_packages(),
      install_requires=requires,
      entry_points={'console_scripts': [
          'mux = muxdemux.cmd_mux:main',
          'demux = muxdemux.cmd_demux:main',
      ],})
