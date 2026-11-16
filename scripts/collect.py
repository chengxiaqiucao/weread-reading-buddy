# -*- coding: utf-8 -*-
"""调用微信读书 Gateway，生成报告 + 档案所需的 bundle.json。

仅依赖 Python 标准库；API Key 从环境变量 WEREAD_API_KEY 读取，任何日志都不输出 key。

用法：
    python scripts/collect.py --out data/bundle.json
"""
import argparse
import io
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

GATEWAY = 'https://i.weread.qq.com/api/agent/gateway'
SKILL_VERSION = '1.0.5'  # Gateway 要求的技能版本，与本包 VERSION 无关
TZ = timezone(timedelta(hours=8))


def today(ts):
    if not ts:
        return ''
    return datetime.fromtimestamp(int(ts), TZ).strftime('%Y-%m-%d')


def now_str():
    return datetime.now(TZ).strftime('%Y-%m-%d %H:%M')


class Gateway:
    def __init__(self, key, delay=0.15):
        self.key = key
        self.delay = delay

    def call(self, api_name, **params):
        body = dict(params)
        body['api_name'] = api_name
        body['skill_version'] = SKILL_VERSION
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(GATEWAY, data=data, method='POST', headers={
            'Authorization': 'Bearer ' + self.key,
            'Content-Type': 'application/json',
        })
        last = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    obj = json.loads(resp.read().decode('utf-8'))
                if isinstance(obj, dict) and obj.get('errcode'):
                    raise RuntimeError('%s 返回 errcode=%s' % (api_name, obj.get('errcode')))
                time.sleep(self.delay)
                return obj or {}
            except Exception as exc:  # 仅重试网络/临时错误，不打印 key
                last = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError('%s 调用失败: %s' % (api_name, last))


def chapter_map(chapters):
    return {str(c.get('chapterUid')): (c.get('chapterIdx') or 0, c.get('title') or '')
            for c in chapters or []}


def collect_book(gw, book, args, news=None):
    bid = str(book.get('bookId') or '')
    if not bid:
        return None
    info = gw.call('/book/info', bookId=bid)
    prog = gw.call('/book/getprogress', bookId=bid)
    pb = prog.get('book') or prog
    chap = gw.call('/book/chapterinfo', bookId=bid)
    cmap = chapter_map(chap.get('chapters'))
    cidx, ctitle = cmap.get(str(pb.get('chapterUid')), (0, ''))

    best = gw.call('/book/bestbookmarks', bookId=bid, chapterUid=0)
    highlights = []
    for i, item in enumerate((best.get('items') or [])[:args.highlights], 1):
        rng = item.get('range') or ''
        reviews = gw.call('/book/readreviews', bookId=bid,
                          chapterUid=item.get('chapterUid'),
                          reviews=[{'range': rng, 'count': 5, 'maxIdx': 0}])
        comments = []
        for group in reviews.get('reviews') or []:
            for pr in group.get('pageReviews') or []:
                rv = pr.get('review') or {}
                comments.append({
                    'content': rv.get('content') or '',
                    'author': (rv.get('author') or {}).get('name') or '',
                    'likes': int(pr.get('likesCount') or 0),
                    'createTime': rv.get('createTime') or 0,
                })
        comments.sort(key=lambda c: c['likes'], reverse=True)
        hidx, htitle = cmap.get(str(item.get('chapterUid')), (0, ''))
        highlights.append({
            'rank': i, 'chapterUid': item.get('chapterUid'), 'chapterTitle': htitle,
            'chapterIdx': hidx, 'range': rng, 'text': item.get('markText') or '',
            'highlightCount': item.get('totalCount') or 0,
            'commentTotal': (reviews.get('reviews') or [{}])[0].get('totalCount') or 0,
            'comments': comments[:3],
        })

    public = gw.call('/review/list', bookId=bid, reviewListType=1, count=30)
    hot_reviews = []
    self_name = os.environ.get('WEREAD_SELF_NAME', '')
    for rv in public.get('reviews') or []:
        outer = rv.get('review') or {}
        inner = outer.get('review') or {}
        if self_name and ((inner.get('author') or {}).get('name') or '') != self_name:
            continue
        hot_reviews.append({
            'content': inner.get('content') or '',
            'author': (inner.get('author') or {}).get('name') or '',
            'star': inner.get('star') or 0,
            'likes': outer.get('likesCount') or 0,
            'comments': outer.get('commentsCount') or 0,
            'createTime': inner.get('createTime') or 0,
            'reviewId': inner.get('reviewId') or '',
        })
        if len(hot_reviews) >= args.reviews:
            break

    marks = gw.call('/book/bookmarklist', bookId=bid)
    bookmarks = [{
        'chapterUid': m.get('chapterUid'), 'chapterTitle': '',
        'markText': m.get('markText') or '', 'range': m.get('range') or '',
        'date': today(m.get('createTime')),
    } for m in (marks.get('updated') or [])[:args.notes]]
    for bm in bookmarks:
        bm['chapterTitle'] = cmap.get(str(bm['chapterUid']), (0, ''))[1]

    mine = gw.call('/review/list/mine', bookid=bid, count=30)
    ideas = [{
        'content': (r.get('review') or {}).get('content') or '',
        'abstract': (r.get('review') or {}).get('abstract') or '',
        'chapterName': (r.get('review') or {}).get('chapterName') or '',
        'chapterIdx': (r.get('review') or {}).get('chapterIdx') or 0,
        'star': (r.get('review') or {}).get('star') or 0,
        'date': today((r.get('review') or {}).get('createTime')),
        'createTime': (r.get('review') or {}).get('createTime') or 0,
    } for r in (mine.get('reviews') or [])[:args.notes]]

    dates = [b['date'] for b in bookmarks if b['date']] + [i['date'] for i in ideas if i['date']]
    base = {
        'bookId': bid, 'title': book.get('title') or info.get('title') or '',
        'author': book.get('author') or info.get('author') or '',
        'cover': book.get('cover') or info.get('cover') or '',
        'rating': info.get('newRating') or 0, 'intro': info.get('intro') or '',
        'wordCount': info.get('wordCount') or 0,
        'totalChapters': len(chap.get('chapters') or []),
        'progress': pb.get('progress') or 0, 'chapterUid': pb.get('chapterUid'),
        'currentChapterTitle': ctitle, 'currentChapterIdx': cidx,
        'lastReadTime': pb.get('updateTime') or book.get('readUpdateTime') or 0,
        'highlightsTotal': best.get('totalCount') or 0,
        'archiveFile': '',  # 由 collect 主流程按书名填充
    }
    result = {
        'base': base, 'highlights': highlights, 'news': news or [],
        'archive': {
            'readingInfo': {'progress': base['progress'], 'chapterUid': base['chapterUid'],
                            'currentChapterIdx': cidx, 'updateTime': base['lastReadTime'],
                            'lastReadDate': today(base['lastReadTime']),
                            'recordReadingTime': pb.get('recordReadingTime') or 0,
                            'finishTime': pb.get('finishTime') or 0},
            'span': {'first': min(dates) if dates else 0, 'last': max(dates) if dates else 0},
            'bookmarkTotal': len(bookmarks), 'ideaTotal': len(ideas),
            'ideasShown': len(ideas), 'bookmarks': bookmarks, 'ideas': ideas,
        },
        'reading': {
            'startReadingTime': pb.get('startReadingTime') or 0,
            'startReadingDate': today(pb.get('startReadingTime')),
            'readingTime': pb.get('readingTime') or 0,
            'ttsTime': pb.get('ttsTime') or 0,
            'lastReadDate': today(base['lastReadTime']),
            'isStartReading': pb.get('isStartReading') or 0,
        },
        'readingReviews': hot_reviews,
        'publicReviews': [],
        '_ideasForGlobal': ideas,
    }
    return result


def collect_friends(gw, limit):
    items = (gw.call('/discover/interact/type3', count=40).get('items') or [])
    groups = {}
    for it in items:
        user = it.get('user') or {}
        name = user.get('name') or it.get('name') or '读者'
        g = groups.setdefault(name, {'name': name,
                                     'latest': it.get('updateTime') or 0,
                                     'following': bool(user.get('isFollowing')),
                                     'follower': bool(user.get('isFollower')),
                                     'books': []})
        g['latest'] = max(g['latest'], it.get('updateTime') or 0)
        bk = it.get('book') or {}
        title = bk.get('title') or ''
        if title and all(x['title'] != title for x in g['books']):
            g['books'].append({'title': title, 'author': bk.get('author') or ''})
    friends = sorted(groups.values(), key=lambda x: (x['latest'], len(x['books'])), reverse=True)
    return friends[:limit]


def collect_stats(gw):
    out = {}
    for mode in ('weekly', 'monthly', 'annually', 'overall'):
        out[mode] = gw.call('/readdata/detail', mode=mode, baseTime=0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data/bundle.json')
    ap.add_argument('--snapshot', default='data/snapshots/last_call.json')
    ap.add_argument('--books', type=int, default=3)
    ap.add_argument('--highlights', type=int, default=10)
    ap.add_argument('--reviews', type=int, default=10)
    ap.add_argument('--notes', type=int, default=100)
    ap.add_argument('--ideas', type=int, default=10)
    ap.add_argument('--friends', type=int, default=5)
    ap.add_argument('--news-dir', default='data/news')
    args = ap.parse_args()

    key = os.environ.get('WEREAD_API_KEY') or ''
    if not key:
        raise SystemExit('未设置 WEREAD_API_KEY 环境变量')
    gw = Gateway(key)

    shelf = gw.call('/shelf/sync')
    candidates = [b for b in (shelf.get('books') or []) if not b.get('finishReading')]
    candidates.sort(key=lambda b: b.get('readUpdateTime') or 0, reverse=True)
    books = []
    for b in candidates[:args.books]:
        bid = str(b.get('bookId') or '')
        news_path = os.path.join(args.news_dir, bid + '.json')
        news = []
        if os.path.exists(news_path):
            with io.open(news_path, encoding='utf-8') as f:
                news = json.load(f)
        arc = collect_book(gw, b, args, news)
        if arc:
            books.append(arc)

    notebooks, last_sort = [], 0
    while True:
        page = gw.call('/user/notebooks', count=100, lastSort=last_sort)
        batch = page.get('books') or []
        notebooks.extend(batch)
        if not page.get('hasMore') or not batch:
            break
        last_sort = batch[-1].get('sort') or 0

    cur = {
        'totalNotes': sum(int(n.get('reviewCount') or 0) + int(n.get('noteCount') or 0) +
                          int(n.get('bookmarkCount') or 0) for n in notebooks),
        'totalBooks': len(notebooks),
        'reviewSum': sum(int(n.get('reviewCount') or 0) for n in notebooks),
        'reviewLikesSum': 0, 'reviewCommentsSum': 0,
        'books': [{'bookId': str(n.get('bookId')), 'title': (n.get('book') or {}).get('title') or '',
                   'review': int(n.get('reviewCount') or 0), 'note': int(n.get('noteCount') or 0),
                   'bookmark': int(n.get('bookmarkCount') or 0)} for n in notebooks],
    }
    recent = []
    for b in books:
        for idea in b.pop('_ideasForGlobal', []):
            recent.append({'chapterIdx': idea.get('chapterIdx') or 0,
                           'content': idea.get('content') or '',
                           'createTime': idea.get('createTime') or 0})
    recent.sort(key=lambda x: x['createTime'], reverse=True)

    prev = {'books': {}, 'notes': cur}
    if os.path.exists(args.snapshot):
        with io.open(args.snapshot, encoding='utf-8') as f:
            prev = json.load(f)
    prev_books = prev.get('books') or {}
    prev_notes = prev.get('notes') or cur

    public_reviews = []
    for b in books:
        for rv in b['readingReviews']:
            public_reviews.append({'bookTitle': b['base']['title'], 'content': rv['content'],
                                   'likes': rv['likes'], 'comments': rv['comments']})
    cur['noteSum'] = sum(int(n.get('noteCount') or 0) for n in notebooks)
    cur['bookmarkSum'] = sum(int(n.get('bookmarkCount') or 0) for n in notebooks)
    cur['publicReviews'] = public_reviews
    cur['reviewLikesSum'] = sum(r['likes'] for r in public_reviews)
    cur['reviewCommentsSum'] = sum(r['comments'] for r in public_reviews)
    for k in ('totalNotes', 'totalBooks', 'reviewSum', 'noteSum', 'bookmarkSum',
              'reviewLikesSum', 'reviewCommentsSum'):
        prev_notes.setdefault(k, cur.get(k, 0))
    prev_notes.setdefault('books', cur['books'])
    prev_notes.setdefault('publicReviews', [])
    for b in books:
        bid = b['base']['bookId']
        old = prev_books.get(bid) or {}
        b['base']['previousProgress'] = old.get('progress', b['base']['progress'])
        b['base']['previousChapterIdx'] = old.get('chapterIdx', b['base']['currentChapterIdx'])
        b['base']['previousChapterTitle'] = old.get('chapterTitle', b['base']['currentChapterTitle'])
        b['base']['archiveFile'] = ''.join(c for c in b['base']['title'] if c not in '\\/:*?"<>|')[:20]
        b['publicReviews'] = []

    bundle = {
        'generatedAt': now_str(),
        'report': {
            'generatedAt': now_str(),
            'books': books,
            'stats': collect_stats(gw),
            'friends': collect_friends(gw, args.friends),
            'notes': {'current': cur, 'previous': prev_notes,
                      'recentIdeas': recent[:args.ideas]},
        },
        'archives': books,
    }

    snapshot = {
        'timestamp': int(time.time()),
        'books': {b['base']['bookId']: {'progress': b['base']['progress'],
                                       'chapterIdx': b['base']['currentChapterIdx'],
                                       'chapterTitle': b['base']['currentChapterTitle'],
                                       'bookmarkTotal': b['archive']['bookmarkTotal'],
                                       'ideaTotal': b['archive']['ideaTotal']} for b in books},
        'notes': cur,
    }
    for path, obj in [(args.out, bundle), (args.snapshot, snapshot)]:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with io.open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    print('bundle ->', args.out)
    print('snapshot ->', args.snapshot)


if __name__ == '__main__':
    main()
