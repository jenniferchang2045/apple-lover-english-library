# ADR 0003：停用闲鱼，改为个人英文书库

日期：2026-09-27

## 决定

项目显示名：**apple_lover个人英文原版书库**  
包名：`apple-lover-english-library` / `apple_lover_library`

闲鱼自营、订单、发货、连接器、百度分享交付全部停止。

锁定：

- 书源 C：本地导入 + Gutenberg / Standard Ebooks 公版下载
- 形态 C：书库 + 导读笔记；用系统程序打开文件

## 后果

- 领域对象从商品包/订单改为 `Book` + `CompanionNote`
- 开发库用 SQLite
- 《酒吧长谈》只保留原创导读为笔记；不提供该小说的下载入口
