# apple_lover个人英文原版书库

个人英文原版阅读。书在本地，笔记在本地。不做闲鱼，不发货。

- 导入你已经拥有的 EPUB / PDF（标 `LICENSED` 或公版）
- 查找：书名、作者都可写片段（不必完全匹配）
- 同时查 Project Gutenberg、Open Library；Google / Standard Ebooks / Internet Archive 用站点内或 `site:` 链接查找
- 可选 AI 扩词（需 `LLM_API_KEY`）：只猜英文书名和作者，不去找盗版
- 只有 Gutenberg（以及 Open Library 里带有 Gutenberg 编号的条目）能一键下载公版 EPUB
- 导读/思维导图作为伴读笔记，用系统默认软件打开

版权期内的书（例如《酒吧长谈》）只记书目和原创导读，没有一键下载。

## 启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
python -m apple_lover_library serve
```

浏览器打开 http://127.0.0.1:8765

## Mind map（Grant Cardone study pack）

成品图片：`content/packages/if-youre-not-first-youre-last/03-mind-map.png`

文字提纲：`content/packages/if-youre-not-first-youre-last/mindmap-sample.json`

思维导图按 `01-introduction-en.txt` 的内容重新设计，为静态图片。导入该书时会将图片复制到书籍目录，不会重新渲染覆盖。日后修改图中的文字，需要重新制作图片并同步更新提纲。

导入的版权书 PDF 在 `library/books/`，不会进 Git。`.env`、`secrets/`、`node_modules/` 也不会进 Git。

常用命令：

```powershell
python -m apple_lover_library list
python -m apple_lover_library search cathedral --author llosa
python -m apple_lover_library search "Pride and Prejudice" --author austen
python -m apple_lover_library download-gutenberg 1342
python -m apple_lover_library import .\my.epub --title "Title" --author "Author" --rights LICENSED
```
