"""
【已废弃，请勿运行】

此文件曾是早期开发时用来生成页面的脚本，把整页 HTML/CSS/JS 写在一个 Python 字符串里。
现在项目已不用这种方式，真正在用的是下面这些文件：

  后端 API     app.py
  标签页       templates/index.html   （HTML + CSS + JS 合一）
  模型管理页   templates/model_tags.html
  跨页持久化   static/persist.js

直接改 templates/*.html 即可，不要运行本脚本。
运行本脚本会用旧版页面覆盖 templates/index.html，导致功能回退。
"""

raise SystemExit(__doc__)
