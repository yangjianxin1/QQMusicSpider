from QQMusicSpider.items import MusicItem
from scrapy import Request
import json
import re
from scrapy.spiders import Spider


# DmozSpider

class QQMusicSpider(Spider):
    # 根据地区area参数筛选歌手，-100:全部，200:内地,2:港台，5:欧美，4:日本，3:韩国，6:其他
    name = "qqmusic"
    start_urls = [
        'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22singerList%22%3A%7B%22module%22%3A%22Music.SingerListServer' \
        '%22%2C%22method%22%3A%22get_singer_list%22%2C%22param%22%3A%7B%22area%22%3A{area}%2C%22sex%22%3A-100%2C%22genr' \
        'e%22%3A-100%2C%22index%22%3A-100%2C%22sin%22%3A{index}%2C%22cur_page%22%3A{cur_page}%7D%7D%7D'
    ]

    # 根据singerid获取歌曲num首歌曲
    song_list_url = "https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22comm%22%3A%7B%22ct%22%3A24%2C%22cv%22%3A0%7D%2C%22singerSongList%22%3A%7B%22method%22%3A%22GetSingerSongList%22%2C%22param%22%3A%7B%22order%22%3A1%2C%22singerMid%22%3A%22{singer_mid}%22%2C%22begin%22%3A{begin}%2C%22num%22%3A{num}%7D%2C%22module%22%3A%22musichall.song_list_server%22%7D%7D"
    # 获取歌词，需要指定song_id
    lyric_url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_yqq.fcg?nobase64=1&musicid={song_id}&format=json"
    # 获取歌词时，必须带上该referer header,需要指定song_mid
    referer = "https://y.qq.com/n/yqq/song/{song_mid}.html"
    # 歌曲评论，需要song_id
    comment_url = 'https://c.y.qq.com/base/fcgi-bin/fcg_global_comment_h5.fcg?biztype=1&topid={song_id}&cmd=8&pagenum={pagenum}&pagesize={pagesize}'
    # 歌曲的url，需要指定song_mid
    song_url = "https://y.qq.com/n/yqq/song/{song_mid}.html"
    # 记录爬虫当前爬取的歌曲数量
    music_num = 0

    def start_requests(self):
        for i in range(1, self.settings.get('SINGER_PAGE_NUM') + 1):  # 在配置信息里获取歌手页数
            # 港台歌手
            request = Request(
                self.start_urls[0].format(index=self.settings.get('SINGER_PAGE_SIZE') * (i - 1), cur_page=i,
                                          area=2),
                callback=self.parse_singer)
            yield request
            # 内地歌手
            request = Request(
                self.start_urls[0].format(index=self.settings.get('SINGER_PAGE_SIZE') * (i - 1), cur_page=i,
                                          area=200),
                callback=self.parse_singer)
            yield request

    def parse_singer(self, response):
        """
        爬取歌手
        """
        singer_list = json.loads(response.text).get('singerList').get('data').get('singerlist')  # 获取歌手列表
        if singer_list:
            for singer in singer_list:
                singer_id = singer.get('singer_id')  # 歌手id
                singer_mid = singer.get('singer_mid')  # 歌手mid
                singer_name = singer.get('singer_name')  # 歌手名字
                singer_pic = singer.get('singer_pic')  # 歌手照片
                for page in range(0, self.settings.get("SONG_PAGE_NUM")):
                    # 爬取歌手的歌曲
                    request = Request(
                        self.song_list_url.format(singer_mid=singer_mid,
                                                  begin=page * self.settings.get('SONG_PAGE_SIZE'),
                                                  num=self.settings.get('SONG_PAGE_SIZE')),
                        callback=self.parse_song)
                    yield request

    def parse_song(self, response):
        """
        爬取歌手的歌曲
        """
        song_list = json.loads(response.text).get('singerSongList').get('data').get("songList")
        if song_list:
            for song in song_list:
                music_item = MusicItem()
                songInfo = song.get('songInfo')
                singer_name = []  # 歌手名字
                singer_id = []
                singer_mid = []
                for singer in songInfo.get('singer'):
                    singer_name.append(singer.get("name"))
                    singer_id.append(singer.get("id"))
                    singer_mid.append(singer.get("mid"))
                music_item["singer_name"] = singer_name  # 歌手名
                music_item["song_name"] = songInfo.get('title')  # 歌曲名字
                music_item["subtitle"] = songInfo.get('subtitle')  # 歌曲子标题,即歌曲名称后面括号的部分
                music_item["album_name"] = songInfo.get('album').get('name')  # 专辑名字
                music_item["singer_id"] = singer_id
                music_item["singer_mid"] = singer_mid
                music_item["song_time_public"] = songInfo.get('time_public')  # 歌曲发布时间
                music_item["song_type"] = songInfo.get('type')  # 歌曲风格，是个数字
                music_item["language"] = songInfo.get('language')  # 歌曲语种，是个数字
                music_item["song_id"] = songInfo.get('id')
                music_item["song_mid"] = songInfo.get('mid')
                music_item["song_url"] = self.song_url.format(song_mid=songInfo.get('mid'))
                request = Request(url=self.comment_url.format(song_id=music_item["song_id"], pagenum=0, pagesize=20),
                                  callback=self.parse_comments,
                                  meta={'music_item': music_item})
                yield request

    def parse_comments(self, response):
        """
        爬取歌曲的评论
        """
        music_item = response.meta.get('music_item')
        hot_comments = json.loads(response.text).get('hot_comment').get('commentlist')  # 精彩评论
        if hot_comments:
            hot_comments = [{'comment_name': comment.get('nick'), 'comment_text': comment.get('rootcommentcontent')} for
                            comment in hot_comments]
        else:
            hot_comments = 'null'
        music_item['hot_comments'] = hot_comments
        # 请求歌词需要加上referer，否则无法返回结果
        request = Request(url=self.lyric_url.format(song_id=music_item["song_id"]),
                          callback=self.parse_lyric,
                          meta={'music_item': music_item})
        request.headers['referer'] = self.referer.format(song_mid=music_item["song_mid"])
        yield request

    def process_lyric(self, lyric):
        """
        处理歌词信息
        :param lyric:
        :return:
        """
        # 返回的单词格式有两种
        re_lyric = re.findall(r'[[0-9]+&#[0-9]+;[0-9]+&#[0-9]+;[0-9]+].*', lyric)
        if re_lyric:  # 以
            lyric = re_lyric[0]
            lyric = lyric.replace("&#32;", " ")
            lyric = lyric.replace("&#40;", "(")
            lyric = lyric.replace("&#41;", ")")
            lyric = lyric.replace("&#45;", "-")
            lyric = lyric.replace("&#10;", "")
            lyric = lyric.replace("&#38;apos&#59;", "'")
            result = []
            for sentence in re.split(u"[[0-9]+&#[0-9]+;[0-9]+&#[0-9]+;[0-9]+]", lyric):
                if sentence.strip() != "":
                    result.append(sentence)
            return "\\n".join(result)
        else:
            lyric = lyric.replace("&#32;", " ")
            lyric = lyric.replace("&#40;", "(")
            lyric = lyric.replace("&#41;", ")")
            lyric = lyric.replace("&#45;", "-")
            lyric = lyric.replace("&#10;", "\\n")
            lyric = lyric.replace("&#38;apos&#59;", "'")
            return lyric

    def parse_lyric(self, response):
        """
        爬取歌曲的歌词
        :param response:
        :return:
        """
        music_item = response.meta.get('music_item')
        response_dict = json.loads(response.text)
        if response_dict["retcode"] == 0:  # 有歌词
            raw_lyric = response_dict["lyric"]
            lyric = self.process_lyric(raw_lyric)
            music_item["lyric"] = lyric
        self.music_num += 1
        print("成功爬取第{}条歌曲".format(self.music_num))
        yield music_item
