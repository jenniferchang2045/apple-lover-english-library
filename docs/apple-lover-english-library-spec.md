# apple_lover个人英文原版书库

**版本**：v0.2  
**日期**：2026-09-27  
**状态**：闲鱼方向已停用，改为个人英文原版阅读

## 一页结论

这是 apple_lover 自己用的英文原版书库，不是售卖平台。

1. 书只存在本机。阅读用系统默认软件打开 EPUB/PDF。
2. 书源 C：已有文件可导入；公版书可从 Project Gutenberg / Standard Ebooks 下载。查找支持不完整书名/作者，并可用 Google（限定合法站点）、Open Library、Internet Archive 与可选 AI 扩词。只有公版 Gutenberg EPUB 提供一键下载。
3. 形态 C：书库目录 + 导读/笔记。第一版不做内置阅读器，不做闲鱼、不做网盘发货。
4. 版权期内作品不能「一键下载」。商业书只能导入你已经合法拥有的文件。
5. 导读、阅读指南、思维导图是 `ORIGINAL` 笔记，不是小说全文。

## 权利

| 类型 | 含义 | 下载 | 导入已有文件 |
| --- | --- | --- | --- |
| PUBLIC_DOMAIN | 公版 / 开放许可目录中的书 | 允许 | 允许 |
| LICENSED | 你已购买或获授权的副本 | 禁止 | 允许 |
| UNKNOWN | 只记书目 | 禁止 | 禁止（可无文件建目） |
| ORIGINAL | 只用于伴读笔记 | 不适用 | 不适用 |

## 本地布局

```text
library/books/{author}/{title}/   原书文件
library/notes/{book_slug}/        导读与思维导图
data/library.db                   SQLite 目录
```
