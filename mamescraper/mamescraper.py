#!/usr/bin/python

# mamescraper 0.1
# author: Pedro Buteri Gonring
# email: pedro@bigode.net
# date: 21/02/2017

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from multiprocessing.pool import ThreadPool
import hashlib
import glob
import os
import sys
import urllib2
import zipfile
import optparse
import json
import time


version = '0.1'


# Parse and validate arguments
def get_parsed_args():
    usage = 'usage: %prog [options]'
    # Get current dir
    cwd = os.getcwd()
    # Create the parser
    parser = optparse.OptionParser(
        description="scrap mame games information and images from "
        "'mame.bigode.net' or 'adb.arcadeitalia.net'",
        usage=usage, version=version
    )
    parser.add_option(
        '-a', '--append', action='store_true', default=False,
        help="scrap only missing roms from output file and append it "
        "to the file (default: disabled)"
    )
    parser.add_option(
        '-d', dest='roms_dir', default=cwd,
        help='directory containing the games (default: current directory)'
    )
    parser.add_option(
        '-f', dest='format', default='zip', choices=('zip', '7z'),
        help="file format of the games: 'zip' or '7z' (default: %default)"
    )
    parser.add_option(
        '-i', dest='images', default='mixed',
        choices=('mixed', 'flyer', 'title'),
        help="images type: 'mixed', 'title' or 'flyer' - mixed will "
        "download a flyer and fallback to title if a flyer is not found "
        "(default: %default)"
    )
    parser.add_option(
        '-o', dest='output_file', default='gamelist.xml',
        help='the xml file that will be created (default: %default)'
    )
    parser.add_option(
        '-s', dest='source', default='bigode', choices=('bigode', 'adb'),
        help="information and images source: 'bigode' or 'adb' "
        "(default: %default)"
    )
    parser.add_option(
        '-w', dest='workers', default=5, type=int,
        help='number of workers threads to use (default: %default)'
    )
    # Parse the args
    (options, args) = parser.parse_args()

    # Some args validation
    if len(args) > 0:
        parser.error(
            "positional argument detected, use 'mamescraper -h' for help"
        )
    if options.workers < 1:
        parser.error('workers must be a positive number')
    return (options, args)


# Get the file MD5 from server
def get_md5():
    headers = {'User-Agent': user_agent}
    req = urllib2.Request(
        scraper_url + 'database_md5.txt', headers=headers
    )
    try:
        md5 = urllib2.urlopen(req).read()
    except urllib2.HTTPError:
        print '\nError: Could not get database MD5'
        print 'Aborting.'
        sys.exit(1)
    return md5


# Calculate MD5 for file
def calc_md5(filename):
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        # iter() with two args needs:
        # First: callable object, in this case an anonymous function
        # Second: 'sentinel, stops iteration when this value is returned
        for block in iter(lambda: f.read(65536), ''):
            md5.update(block)
    return md5.hexdigest()


# Download mame database
def get_mame_db(db_zip_file):
    # Set user agent and download with a progress percentual
    headers = {'User-Agent': user_agent}
    req = urllib2.Request(
        scraper_url + os.path.basename(db_zip_file), headers=headers
    )
    try:
        resp = urllib2.urlopen(req)
        length = int(resp.info()['content-length'])
        downloaded = 0
        one_perc = length / 100
        with open(db_zip_file, 'wb') as f:
            for chunk in iter(lambda: resp.read(16384), ''):
                downloaded += len(chunk)
                f.write(chunk)
                # '\r\x1b[K' == '\r'    Carriage Return
                #               '\x1b[' Control Sequence Initiator
                #               'K'     EL - Erase in Line
                sys.stdout.write(
                    '\r\x1b[K Downloading: %d%%' % (downloaded / one_perc)
                )
                sys.stdout.flush()
        resp.close()
    except urllib2.HTTPError:
        print '\nError: Could not download mame xml database'
        print 'Aborting.'
        sys.exit(1)

    # Unzip file
    mame_database_zip = zipfile.ZipFile(db_zip_file, 'r')
    try:
        mame_database_zip.extractall()
    except:
        print '\nError: Could not extract zip file, probably corrupted'
        print 'Aborting.'
        sys.exit(1)
    mame_database_zip.close()
    os.remove(db_zip_file)


# Return a list of games found in database xml
def get_match_list(mame_database_xml, romlist):
    match_list = []
    for game in mame_database_xml.iter('game'):
        rom = game.attrib.get('name')
        if rom in romlist:
            match_list.append(rom)
    return match_list


# Create needed resources for 'bigode' source
def init_bigode(romlist):
    db_zip_file = os.path.join(options.roms_dir, 'mame_database.zip')
    db_xml_file = os.path.join(options.roms_dir, 'mame_database.xml')

    # Check and download mame_database.xml if needed
    mame_database_md5 = get_md5().rstrip()
    if os.path.isfile(db_xml_file):
        print '\nMame database xml found'
        md5 = calc_md5(db_xml_file)
        if md5 == mame_database_md5:
            print ' MD5 check: OK'
        else:
            print ' MD5 check: FAIL'
            print ' Downloading new database xml...'
            get_mame_db(db_zip_file)
            print '\nDone!'
    else:
        print '\nMame database xml not found'
        get_mame_db(db_zip_file)
        print '\nDone!'

    print '\nGenerating list of images to download...'

    # Open and read the database xml
    with open(db_xml_file, 'r') as f:
        mame_database_xml = ET.parse(f)

    # Create match list
    match_list = get_match_list(mame_database_xml, romlist)
    print 'Done!'
    return mame_database_xml, match_list


# Get information from adb
def get_info_adb(rom):
    headers = {'User-Agent': user_agent}
    query = 'service_scraper.php?ajax=query_mame&lang=en&game_name=' + rom
    req = urllib2.Request(
        scraper_url + query, headers=headers
    )
    try:
        resp = urllib2.urlopen(req).read()
    except Exception as ex:
        return 'URL: %s - Error: %s' % (scraper_url + query, ex)

    # Parse information
    data = json.loads(resp)
    try:
        data = data['result'][0]
    except IndexError:
        return '%s information NOT FOUND' % rom
    except Exception as ex:
        return 'URL: %s - Error: %s' % (scraper_url + query, ex)
    game = {}
    game['players'] = data['players']
    game['name'] = data['title']
    game['releasedate'] = data['year']
    game['genre'] = data['genre']
    game['developer'] = data['manufacturer']
    try:
        history = data['history'].splitlines()
        history = filter(None, history)
        game['desc'] = history[1]
    except:
        game['desc'] = ''
    return game


# Generate gamelist for bigode source
def generate_gamelist_bigode(mame_database_xml, romlist, gamelist_xml=''):
    if options.append:
        gamelist = gamelist_xml.getroot()
    else:
        # Start the new gamelist xml
        gamelist = ET.Element('gameList')

    # Populate the new gamelist xml
    for game in mame_database_xml.iter('game'):
        rom = game.attrib.get('name')
        if rom in romlist:
            # Create new game entry
            gameitem = ET.SubElement(gamelist, 'game')
            # Set rom path
            path = './%s.%s' % (rom, options.format)
            ET.SubElement(gameitem, 'path').text = path
            # Set name
            name = game.find('fullname').text
            if name is None:
                ET.SubElement(gameitem, 'name').text = rom
            else:
                ET.SubElement(gameitem, 'name').text = name
            # Set description
            desc = game.find('desc').text
            ET.SubElement(gameitem, 'desc').text = desc
            # Set image path
            if rom in not_found_imgs:
                ET.SubElement(gameitem, 'image').text = ''
            else:
                ET.SubElement(
                    gameitem, 'image').text = './images/' + rom + '.png'
            # Set rating
            rating = game.find('rating').text
            ET.SubElement(gameitem, 'rating').text = rating
            # Set release date
            releasedate = game.find('releasedate').text
            ET.SubElement(gameitem, 'releasedate').text = releasedate
            # Set developer
            developer = game.find('developer').text
            ET.SubElement(gameitem, 'developer').text = developer
            # Set genre
            genre = game.find('genre').text
            ET.SubElement(gameitem, 'genre').text = genre
            # Set players
            players = game.find('players').text
            ET.SubElement(gameitem, 'players').text = players
    return gamelist


# Generate gamelist for adb source
def generate_gamelist_adb(adb_found, gamelist_xml=''):
    if options.append:
        gamelist = gamelist_xml.getroot()
    else:
        gamelist = ET.Element('gameList')

    # Populate the new gamelist
    for game in adb_found:
        # Create new game entry
        gameitem = ET.SubElement(gamelist, 'game')
        # Set rom path
        path = './%s.%s' % (game['rom'], options.format)
        ET.SubElement(gameitem, 'path').text = path
        # Set name
        name = game['name']
        if name is None:
            ET.SubElement(gameitem, 'name').text = game['rom']
        else:
            ET.SubElement(gameitem, 'name').text = name
        # Set description
        ET.SubElement(gameitem, 'desc').text = game['desc']
        # Set image path
        if 'image' in game:
            ET.SubElement(gameitem, 'image').text = game['image']
        else:
            ET.SubElement(gameitem, 'image').text = ''
        # Set release date
        ET.SubElement(gameitem, 'releasedate').text = game['releasedate']
        # Set developer
        ET.SubElement(gameitem, 'developer').text = game['developer']
        # Set genre
        ET.SubElement(gameitem, 'genre').text = game['genre']
        # Set players
        ET.SubElement(gameitem, 'players').text = game['players']
    return gamelist


# Indent xml
# Taken from "http://effbot.org/zone/element-lib.htm#prettyprint"
def indent_xml(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent_xml(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


# Download images
def download_image(rom, img_type, source):
    filename = rom + '.png'
    headers = {'User-Agent': user_agent}
    if source == 'adb':
        img_url = '%s?type=%s&resize=0&mame=%s' % (scraper_url, img_type, rom)
    elif source == 'bigode':
        img_url = scraper_url + img_type + 's/' + filename
    # Check if file exists
    if os.path.isfile(os.path.join(images_dir, filename)):
        return '%s exists skipping download' % filename
    # Download image
    try:
        req = urllib2.Request(img_url, headers=headers)
        img = urllib2.urlopen(req).read()
    except urllib2.HTTPError:
        return '%s NOT FOUND' % filename
    except Exception as ex:
        return 'URL: %s - Error: %s' % (img_url, ex)
    if len(img) == 0:
        return '%s NOT FOUND' % filename
    # Save image
    with open(os.path.join(images_dir, filename), 'wb') as f:
        f.write(img)
    return '%s downloaded' % filename


# Download images based on option
def download_img_type(rom, source):
    if options.images == 'mixed':
        down_msg = download_image(rom, 'flyer', source)
        if 'NOT FOUND' in down_msg or 'Error' in down_msg:
            down_msg = download_image(rom, 'title', source)
    elif options.images == 'title':
        down_msg = download_image(rom, 'title', source)
    elif options.images == 'flyer':
        down_msg = download_image(rom, 'flyer', source)
    return down_msg


# Return the parsed xml and a list of existing games
def get_existing_games(output_file):
    existing_games = []
    if os.path.isfile(output_file):
        with open(output_file, 'r') as f:
            try:
                gamelist_xml = ET.parse(f)
            except:
                print '\nError: %s is not a valid xml' %\
                    os.path.basename(output_file)
                sys.exit(1)
        for game in gamelist_xml.iter('game'):
            try:
                # Infer rom name based on path
                rom = game.find('path').text
                rom = rom.split('/')[-1]
                rom = rom.replace('.zip', '').replace('.7z', '')
                existing_games.append(rom)
            except:
                pass
        return gamelist_xml, existing_games
    else:
        print '\nError: %s does not exist' % os.path.basename(output_file)
        sys.exit(1)


# Sort gamelist
def sort_gamelist(gamelist):
    games = gamelist.findall('game')
    # sorted() can receive a function as the 'key' to sort
    games = sorted(games, key=lambda k: k.findtext('name'))
    gamelist.clear()
    for game in games:
        gamelist.append(game)
    return gamelist


# Indent and write to disk the new gamelist xml
def save_gamelist_xml(gamelist, output_file):
    indent_xml(gamelist)
    tree = ET.ElementTree(gamelist)
    tree.write(output_file, xml_declaration=True, encoding='UTF-8')


# Create and start thread pool of workers
def init_workers(romlist):
    pool = ThreadPool(processes=options.workers)
    try:
        # .get(2592000) will set the pool timeout to one month
        # Setting a timeout is needed to catch keyboard interrupt
        pool.map_async(work_work, romlist).get(2592000)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        print 'Aborting.'
        sys.exit(1)


# Worker function
def work_work(rom):
    if options.source == 'bigode':
        down_msg = download_img_type(rom, 'bigode')
        sys.stdout.write(' ' + down_msg + '\n')
        sys.stdout.flush()
        if 'download' not in down_msg:
            not_found_imgs.append(rom)

    elif options.source == 'adb':
        game = get_info_adb(rom)
        if type(game) == dict:
            down_msg = download_img_type(rom, 'adb')
            if 'download' in down_msg:
                game['image'] = './images/' + rom + '.png'
            game['rom'] = rom
            adb_found.append(game)
            sys.stdout.write(
                ' %s information scrapped' % rom + '\n ' + down_msg + '\n'
            )
            sys.stdout.flush()
        else:
            sys.stdout.write(' ' + game + '\n')
            sys.stdout.flush()


# Main CLI
def cli():
    global options
    global user_agent
    global scraper_url
    global images_dir
    global not_found_imgs
    global adb_found

    (options, args) = get_parsed_args()

    user_agent = 'mamescraper/%s (%s)' % (version, sys.platform)
    output_file = os.path.join(options.roms_dir, options.output_file)
    images_dir = os.path.join(options.roms_dir, 'images')
    # Store roms that do not have images on bigode source
    not_found_imgs = []
    # Store the games information found on adb
    adb_found = []
    # Store init time
    init_time = time.time()

    print '\nInitializing the scraper...'

    # Generate list of roms to scrape
    romlist = glob.glob('*.' + options.format)
    romlist = [item.replace('.' + options.format, '') for item in romlist]

    # Parse existing gamelist and generate new romlist if append enable
    if options.append:
        gamelist_xml, existing_games = get_existing_games(output_file)
        romlist = list(set(romlist) - set(existing_games))

    # Quit if no games to scrap
    if len(romlist) == 0:
        print '\nNo roms to scrap, quitting...'
        sys.exit(1)

    # Create images directory if not exists
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    print '\nScraping from: %s' % options.source

    # Init the scraper for correct source
    if options.source == 'bigode':
        scraper_url = 'http://mame.bigode.net/'
        mame_database_xml, match_list = init_bigode(romlist)
        print '\nDownloading %d images:' % len(match_list)
        init_workers(match_list)
        print 'Done!'

    elif options.source == 'adb':
        scraper_url = 'http://adb.arcadeitalia.net/'
        print '\nScraping %d games:' % len(romlist)
        init_workers(romlist)
        print 'Done!'

    # Create list of not found games
    if options.source == 'bigode':
        not_found = list(set(romlist) - set(match_list))
        not_found.sort()
    elif options.source == 'adb':
        adb_match = [game['rom'] for game in adb_found]
        not_found = list(set(romlist) - set(adb_match))
        not_found.sort()

    #  Print not found games if needed
    if len(not_found) > 0:
        print '\nGames not found:'
        for item in not_found:
            print ' %s' % item
        print 'Total: %d' % len(not_found)

    # Quit if we dont need to generate xml
    if (options.source == 'bigode' and len(match_list) == 0) or\
            (options.source == 'adb' and len(adb_found) == 0):
        print '\nNo game information found, quitting...'
        sys.exit(1)

    print '\nGenerating new gamelist xml...'

    # Generate new gamelist for correct source
    if options.source == 'bigode':
        if options.append:
            gamelist = generate_gamelist_bigode(
                mame_database_xml, match_list, gamelist_xml
            )
            gamelist = sort_gamelist(gamelist)
        else:
            gamelist = generate_gamelist_bigode(mame_database_xml, match_list)
        # Write gamelist to disk
        save_gamelist_xml(gamelist, output_file)

    elif options.source == 'adb':
        if options.append:
            gamelist = generate_gamelist_adb(adb_found, gamelist_xml)
            gamelist = sort_gamelist(gamelist)
        else:
            adb_found = sorted(adb_found, key=lambda k: k['name'])
            gamelist = generate_gamelist_adb(adb_found)
        save_gamelist_xml(gamelist, output_file)

    print ' New ' + options.output_file + ' file created!'

    # Calc and print time spent
    time_spent = int(time.time() - init_time)
    print '\nTotal time spent: %dm %ds' % (time_spent / 60, time_spent % 60)

    print '\nAll set! Happy gaming :)'


# Run cli function if invoked from shell
if __name__ == '__main__':
    cli()
