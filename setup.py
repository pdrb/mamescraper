from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


version = '0.1'


setup(
    name='mamescraper',
    version=version,
    description='scrap mame games information and images',
    long_description=long_description,
    author='Pedro Buteri Gonring',
    author_email='pedro@bigode.net',
    url='https://github.com/pdrb/mamescraper',
    license='MIT',
    classifiers=[],
    keywords='mame scraper games roms emulationstation retropie recalbox',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    entry_points={
        'console_scripts': ['mamescraper=mamescraper.mamescraper:cli'],
    },
)
