# -*- coding: utf-8 -*-
"""把数据 JSON 注入 HTML 模板，生成可直接打开的报告 / 读书档案。

用法：
    python scripts/render.py report  data/samples/report.json            out/个人阅读报告.html
    python scripts/render.py archive data/samples/archives/31131759.json out/读书档案/剑来_读书档案.html
    python scripts/render.py all     data/bundle.json                    out/

bundle.json 结构：{"report": {报告数据}, "archives": [档案数据, ...]}
"""
import argparse
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLACEHOLDER = '__WEREAD_DATA__'


def load(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def render(kind, data, out):
    tpl_path = os.path.join(ROOT, 'templates', kind + '.html')
    with io.open(tpl_path, encoding='utf-8') as f:
        tpl = f.read()
    assert tpl.count(PLACEHOLDER) == 1, '模板数据占位符异常: ' + tpl_path
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    html = tpl.replace(PLACEHOLDER, payload)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['report', 'archive', 'all'])
    ap.add_argument('data')
    ap.add_argument('out')
    args = ap.parse_args()

    if args.kind == 'all':
        bundle = load(args.data)
        render('report', bundle['report'], os.path.join(args.out, '个人阅读报告.html'))
        for arc in bundle.get('archives', []):
            name = (arc['base'].get('archiveFile') or arc['base']['title'][:12]).replace('_读书档案', '')
            render('archive', arc, os.path.join(args.out, '读书档案', name + '_读书档案.html'))
    else:
        render(args.kind, load(args.data), args.out)


if __name__ == '__main__':
    main()
