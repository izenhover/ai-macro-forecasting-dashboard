"""دریافت اخبار زنده از RSS"""

import feedparser
from datetime import datetime
from loguru import logger

FEEDS = {
    "farsnews": "https://www.farsnews.ir/rss/economy",
    "mehr": "https://www.mehrnews.com/rss/tp/34",
    "reuters": "https://feeds.reuters.com/reuters/businessNews",
    "donya": "https://donya-e-eqtesad.com/rss",
}


def fetch_news(limit_per_source=5):
    """دریافت اخبار از منابع RSS"""
    all_news = []
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= limit_per_source:
                    break
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "")[:300].strip()
                if not title:
                    continue
                all_news.append({
                    "title": title,
                    "summary": summary,
                    "source": source,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                })
                count += 1
            logger.info("   news " + source + ": " + str(count))
        except Exception as e:
            logger.warning("   news " + source + " failed: " + str(e))
    return all_news


def get_sample_news():
    """اخبار نمونه در صورت عدم دسترسی به RSS"""
    return [
        {"title": "قیمت طلا در بازار جهانی افزایش یافت", "summary": "", "source": "farsnews", "link": "", "published": ""},
        {"title": "تحریم‌های جدید علیه صادرات نفت ایران اعمال شد", "summary": "", "source": "reuters", "link": "", "published": ""},
        {"title": "نرخ دلار در بازار آزاد به بالاترین سطح رسید", "summary": "", "source": "donya", "link": "", "published": ""},
        {"title": "توافق تجاری جدید بین ایران و چین امضا شد", "summary": "", "source": "mehr", "link": "", "published": ""},
        {"title": "تنش‌های سیاسی در منطقه خاورمیانه تشدید شد", "summary": "", "source": "reuters", "link": "", "published": ""},
        {"title": "افزایش نقدینگی و فشار تورمی در اقتصاد ایران", "summary": "", "source": "donya", "link": "", "published": ""},
    ]
