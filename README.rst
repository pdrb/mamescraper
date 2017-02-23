mamescraper
===========

Scrap mame games information and images from 'mame.bigode.net' or
'adb.arcadeitalia.net' and generate a xml for use with EmulationStation.

About
-----

The purpose of this scraper is to be simple and fast. Currently it supports
two sources with drastically different scraping methodologies.

The default source (bigode) is a lot faster because the scraper will download
an entire mame database (1.1MB compressed) and scrap all the games information
in one go. Besides that, this source uses a CDN and a very fast webserver to
serve the images, resulting in faster responses and downloading speed overall.

The adb source is a more traditional approach, for each game found, the scraper
will do a http request to get the information needed and then will download the
appropriate image.

It is important to note that the images flyers on 'bigode' source are smaller
in size, because they have a fixed 400 width.

To illustrate the difference in scraping speed, the following shows the time
spent scraping an entire mame 037b5 set (2241 roms) on both sources:

'bigode' source:

::

    Command: mamescraper -w 10 -i title
    Time spent: 1m 10s

'adb' source:

::

    Command: mamescraper -w 10 -i title -s adb
    Time spent: 8m 29s

Note that mamescraper was run with 10 workers and scraping titles only. If ran
in 'mixed' image mode (default) the difference is even higher, since images
flyers are bigger on adb:

'bigode' source:

::

    Command: mamescraper -w 10
    Time spent: 2m 2s


'adb' source:

::

    Command: mamescraper -w 10 -s adb
    Time spent: 26m 47s

Based on that, the recommended way is to run using the default 'bigode' source
and if a game is not found, just run the scraper again in 'append' mode
(to scan only the missing games) using 'adb' as source.

A huge thanks for AntoPISA creator of `Progetto Snaps <http://www.progettosnaps.net/>`_
for the images and tons of mame resources.

Also, a huge thanks to Motoschifo creator of `Arcade Database <http://adb.arcadeitalia.net/>`_
for the awesome arcade database website.

Install
-------

Install using pip:

::

    pip install mamescraper

or

Download and set executable permission on the script file:

::

    chmod +x mamescraper.py

or

Download and run using the python interpreter:

::

    python mamescraper.py

or

Download the Windows executable file from the `releases <https://github.com/pdrb/mamescraper/releases>`_ page.

Usage
-----

::

    Usage: mamescraper.py [options]

    scrap mame games information and images from 'mame.bigode.net' or
    'adb.arcadeitalia.net'

    Options:
    --version           show program's version number and exit
    -h, --help          show this help message and exit
    -a, --append        scrap only missing roms from output file and append it
                        to the file (default: disabled)
    -d ROMS_DIR         directory containing the games (default: current
                        directory)
    -e IMAGES_DIR_NAME  directory name to download the images (default: images)
    -f FORMAT           file format of the games: 'zip' or '7z' (default: zip)
    -i IMAGES           images type: 'mixed', 'title' or 'flyer' - mixed will
                        download a flyer and fallback to title if a flyer is not
                        found (default: mixed)
    -o OUTPUT_FILE      the xml file that will be created (default:
                        gamelist.xml)
    -s SOURCE           information and images source: 'bigode' or 'adb'
                        (default: bigode)
    -w WORKERS          number of workers threads to use (default: 5)

Examples
--------

Simplest use case is to run on the mame games directory itself:

::

    $ cd my_games_dir
    $ mamescraper

Alternatively, you can pass the directory to the scraper:

::

    $ mamescraper -d path_to_games_dir

Scrap only missing games in the existing 'gamelist.xml' file:

::

    $ mamescraper -a

It is useful for scrap on both sources if a game is not found. Just run the
scraper a second time with append enable and a different source:

::

    $ mamescraper
    $ mamescraper -a -s adb

If you have games in mixed formats, the following will run the first time
scraping games in 'zip' format (default) and the second time appending the
missing games in '7z' format:

::

    $ mamescraper
    $ mamescraper -a -f 7z

Run with 10 workers downloading only titles images:

::

    $ mamescraper -i title -w 10

Notes
-----

- Works on Python 2
- Tested on Linux and Windows, but should work on all platforms
- Uses only Python standard library for maximum compatibility
