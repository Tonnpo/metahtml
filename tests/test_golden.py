#!/usr/bin/python3

from urllib.parse import urlparse, urlunparse
import copy
import csv
import datetime
import glob
import hashlib
import json
import os
import pprint
import pytest
import re
import requests
    
# the sys import is needed so that we can import from the current project
import sys
sys.path.append('.')
import metahtml

################################################################################
# settings

cache_dir = 'tests/.cache'
golden_dir = 'tests/.golden'
golden_full_dir = 'tests/.golden_full'

################################################################################
# utility functions for caching webpages

def url2filename(url):
    '''
    Many characters in urls cannot be included in filenames.
    This function modifies the url so that it can safely be stored on disk,
    while attempting to keep the url as human-readable as possible.
    In particular:
        1. the length of the url is truncated,
        2. all potentially invalid characters are replaced with underscores, and
        3. an md5 hash is added at the end to prevent name collisions.
    We don't rely on just the md5 hash because we want the filename to be human readable.
    '''
    return re.sub(r'[/:><"|*?&]','_',url)[:196] + hashlib.md5(url.encode()).hexdigest()[:8]


def get_cached_webpages(url, dates=None, redownload=False):
    '''
    If the url does not exit in the cache,
    then this function first downloads the html and stores it in the cache.
    Next, it returns the result of the cache.
    This function is slow to run on the first call for each url,
    but then fast on all subsequent calls.
    '''
    url_filename = url2filename(url)

    # create the cache folder for the url if it doesn't exist
    url_dir = os.path.join(cache_dir,url_filename)
    os.makedirs(url_dir, exist_ok=True)

    # get the filenames that correspond to the input url/dates combo
    if dates is None:
        globpath = os.path.join(url_dir,'????-??-??')
        paths = glob.glob(globpath)
    else:
        paths = [ os.path.join(url_dir, date) for date in dates ]

    # if no filenames found, then add the url to the cache with the current date
    def download_url():
        print('downloading url=',url,end=' ... ')
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        path = os.path.join(url_dir,date)
        paths = [ path ]
        r = requests.get(url,headers={'User-Agent':'Mozilla/5.0 (X11; Linux i686; rv:88.0) Gecko/20100101 Firefox/88.0'},verify=False)
        print("r.encoding=",r.encoding)
        #if r.status_code != 200:
        #    raise ValueError('status=',r.status_code,'for url=',url)
        html = r.text
        with open(path,'x', encoding='utf-8', newline='\n') as f:
            f.write(html)
    if len(paths)==0 or redownload:
        download_url()
        return get_cached_webpages(url, dates)

    # return the contents of the cache
    ret = []
    for path in paths:
        try:
            with open(path, encoding='utf-8', newline='\n') as f:
                ret.append((os.path.basename(path),f.read()))
        except FileNotFoundError:
            download_url()
    return ret


################################################################################
# test cases

def generate_test(url, verbose=True, fast=True, save=False, debug=False, full=False, save_full=False, redownload=False):
    '''
    Prints the simplified meta for the url to stdout.
    If save is True, it also generates a golden test from the result.
    Save should only be set to True after the output has been manually verified.
    '''
    if save:
        fast = False
        full = False

    for date, html in get_cached_webpages(url, redownload=redownload):

        # generate the test path
        url_filename = url2filename(url)
        url_dir = os.path.join(golden_dir,url_filename)
        os.makedirs(url_dir, exist_ok=True)
        test_path = os.path.join(url_dir,date)

        # generate the test information
        meta = metahtml.parse_for_testing(html, url, fast=fast, debug=debug)
        output = json.dumps(
            dict(meta),
            indent=4,
            sort_keys=True,
            default=str
            )

        # print/save as specified in the options
        if verbose:
            print("test_path=",test_path)
            print(output)

        if save:
            with open(test_path,'x', encoding='utf-8', newline='\n') as f:
                f.write(output)

        if full or save_full:
            meta = metahtml.parse(html, url)
            output = json.dumps(
                dict(meta),
                default=str
                )
            url_dir = os.path.join(golden_full_dir,url_filename)
            os.makedirs(url_dir, exist_ok=True)
            full_path = os.path.join(url_dir,date)
            if full:
                print("full_path=",full_path)
                print(output)

            if save_full:
                with open(full_path,'x', encoding='utf-8', newline='\n') as f:
                    f.write(output)


def get_tests(cache_filter=True):
    '''
    Returns a list of test cases.

    NOTE:
    The returned test cases are guaranteed to exist in both the golden_dir and the cache_dir.
    The true values are stored in the golden_dir, and these should exist in all clones of the repo.
    The raw html for running the code is stored in the cache_dir.
    Because this can be a very large amount of data,
    it is possible to do a sparse clone and not acquire all this data.
    This function does not generate test cases for those tests that have not been downloaded.
    '''
    raw_tests = glob.glob(os.path.join(os.path.join(os.path.join(golden_dir,'*')),'*'))

    if not cache_filter:
        return raw_tests

    def has_cache(test_file):
        date = os.path.basename(test_file)
        url_filename = os.path.basename(os.path.dirname(test_file))
        cache_file = os.path.join(os.path.join(cache_dir, url_filename), date)
        return os.path.exists(cache_file)

    return list(filter(has_cache, raw_tests))


@pytest.mark.parametrize('test_file', get_tests())
def test_golden(test_file, full=False):
    '''
    This function gets called by pytest for each golden test case.
    It checks that for each url/date combination,
    the stored golden meta and a freshly generated meta are equal.
    '''

    # extract the golden result
    with open(test_file, encoding='utf-8') as f:
        meta_golden = json.loads(f.read())

    # get the url/date being tested
    url = meta_golden['url']
    date = os.path.basename(test_file)

    # compute the meta from scratch
    [(date, html)] = get_cached_webpages(url, [date])
    if full:
        metahtml.parse(html, url, fast=False)
    meta = metahtml.parse_for_testing(html, url, fast=False)

    # run the test;
    # for most keys we need an exact match to pass;
    # the way that the 'type' key is currently handled, however, all types != 'article' are equivalent
    for k in meta_golden.keys():
        if k=='type':
            assert (meta_golden[k] == 'article' and meta[k] == 'article') or (meta_golden[k] != 'article' and meta[k] != 'article')
        else:
            assert meta_golden[k] == meta[k]


def convert_csv(filter_str=None, filter_key=None, verified_only=True):
    '''
    This function only needs to be called once to convert from the old style tests to the new.
    '''
    tests = []
    golden_test_file = 'tests/golden.csv'
    with open(golden_test_file, 'rt', encoding='utf-8', newline='\n') as f:
        for line,test in enumerate(csv.DictReader(f, dialect='excel', strict=True)):

            # csv files store both the None and '' values in the same format;
            # we assume that we never store '' values, 
            # and therefore they should always be None instead 
            for k,v in test.items():
                if v=='':
                    test[k] = None

            # filter based on human_verified
            if filter_str is not None and filter_key is not None:
                if filter_str in test[filter_key]:
                    tests.append(test)
            else:
                valid_annotator = test['human_annotator'] is not None and test['human_annotator'][:4] != 'skip'
                if not verified_only or valid_annotator:
                    tests.append(test)
    
    num_processed = 0
    for i,test in enumerate(tests):
        url_filename = url2filename(test['url'])
        url_dir = os.path.join(golden_dir,url_filename)
        if not os.path.exists(url_dir):
            generate_test(test['url'], verbose=False, save=True)
            print("test['url']=",test['url'])
            num_processed += 1
    return tests


################################################################################
# initialize the test cases

if __name__=='__main__':

    # process command line args
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--slow', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--redownload', action='store_true')
    args = parser.parse_args()

    generate_test(args.url, not args.full, not args.slow, args.save, args.debug, args.full, redownload=args.redownload)
