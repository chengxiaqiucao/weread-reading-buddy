# -*- coding: utf-8 -*-
"""模板渲染冒烟测试：不依赖 API Key。"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')


class RenderTest(unittest.TestCase):
    def test_render_all(self):
        with tempfile.TemporaryDirectory() as td:
            cmd = [sys.executable, os.path.join(SCRIPTS, 'render.py'), 'all',
                   os.path.join(ROOT, 'data', 'bundle_sample.json'), td]
            subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True)

            report = os.path.join(td, '个人阅读报告.html')
            archive = os.path.join(td, '读书档案', '剑来_读书档案.html')
            self.assertTrue(os.path.exists(report))
            self.assertTrue(os.path.exists(archive))

            with io.open(report, encoding='utf-8') as f:
                html = f.read()
            self.assertNotIn('__WEREAD_DATA__', html)
            self.assertIn('previousProgress', html)
            self.assertIn('展开其余', html)
            self.assertNotIn('数据说明', html)
            self.assertNotIn('账号全局', html)
            self.assertIn('读书档案/', html)

            with io.open(archive, encoding='utf-8') as f:
                arc = f.read()
            self.assertNotIn('__WEREAD_DATA__', arc)
            self.assertIn('refl-mask', arc)
            self.assertIn('开始编写', arc)
            self.assertIn('../个人阅读报告.html', arc)
            self.assertNotIn('口径说明', arc)

    def test_samples_valid(self):
        with io.open(os.path.join(ROOT, 'data', 'samples', 'report.json'), encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(len(data['books']), 3)
        self.assertIn('recentIdeas', data['notes'])
        for p in os.listdir(os.path.join(ROOT, 'data', 'samples', 'archives')):
            with io.open(os.path.join(ROOT, 'data', 'samples', 'archives', p), encoding='utf-8') as f:
                arc = json.load(f)
            self.assertIn('reading', arc)
            self.assertIn('readingReviews', arc)


if __name__ == '__main__':
    unittest.main()
