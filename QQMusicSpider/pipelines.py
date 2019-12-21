# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from QQMusicSpider.items import MusicItem
import json
from scrapy.exceptions import DropItem


class DuplicatesPipeline(object):
    """
    根据音乐的song_id，对爬取过的音乐进行去重
    """

    def __init__(self):
        self.song_ids = set()

    def process_item(self, item, spider):
        if isinstance(item, MusicItem):
            if item['song_id'] in self.song_ids:
                raise DropItem("Duplicate item found: %s" % item)
            else:
                self.song_ids.add(item['song_id'])
                return item


class QqmusicspiderPipeline(object):
    def __init__(self):
        music_path = "music"
        self.file = open(music_path, "w", encoding="utf8")

    def process_item(self, item, spider):
        if isinstance(item, MusicItem):
            line = json.dumps(dict(item), ensure_ascii=False) + "\n"
            self.file.write(line)
        return item

    def close_spider(self, spider):
        self.file.close()
