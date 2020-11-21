'''
'''

from metahtml.property.__common__ import BaseExtractor

class Extractor(BaseExtractor):

    def custom_patterns(parser, results):

        # get page translations for websites following html5 standard
        urls = {}
        xpath = '//link[@rel="alternate"]'
        for element in parser.doc.xpath(xpath):
            hreflang = element.attrib.get('hreflang')
            href = element.attrib.get('href')
            if href[:2]=='//':
                href = parser.url_parsed.scheme+':'+href
            if hreflang is not None and href is not None:
                urls[hreflang]=href
        results.append({
            'value'     : urls,
            'pattern'   : xpath
            })

        # custom websites
        if 'english.khan.co.kr' in parser.url_parsed.hostname:
            urls = {}
            xpath = '//div[@class="article_txt"]/a'
            for element in parser.doc.xpath(xpath):
                hreflang = 'ko'
                href = element.attrib.get('href')
                if href[:2]=='//':
                    href = parser.url_parsed.scheme+':'+href
                if hreflang is not None and href is not None:
                    urls[hreflang]=href
            results.append({
                'value'     : urls,
                'pattern'   : xpath
                })

        if 'news.khan.co.kr' in parser.url_parsed.hostname:
            urls = {}
            xpath = '//div[@class="btn_engtrans"]/a'
            for element in parser.doc.xpath(xpath):
                hreflang = 'en'
                href = element.attrib.get('href')
                if href[:2]=='//':
                    href = parser.url_parsed.scheme+':'+href
                if hreflang is not None and href is not None:
                    urls[hreflang]=href
            results.append({
                'value'     : urls,
                'pattern'   : xpath
                })

        # FIXME:
        # add the following non-standard pages
        # http://english.khan.co.kr/khan_art_view.html?artid=202005221946377
        # https://www.dailynk.com/english/source-kim-jong-un-recently-cardiovascular-operation/
        # https://mainichi.jp/english/articles/20200523/p2a/00m/0na/023000c
        # https://mondediplo.com/2020/05/03covid-ecology
        # https://carnegie-mec.org/diwan/81781
        # https://www.cdc.gov/flu/pandemic-resources/pandemic-timeline-1930-and-beyond.htm

        # direct translations without links:
        # https://bles.com/mundo/rusia-uso-hidroxicloroquina-medicamento-tratar-virus-pcch-sugerido-trump.html
        # https://thebl.com/world-news/russia-supports-hydroxychloroquine-drug-ccp-virus-trump.html

        return results

