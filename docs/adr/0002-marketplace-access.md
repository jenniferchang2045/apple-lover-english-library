# ADR 0002：闲鱼接入策略

日期：2026-09-05

## 官方公开能力

来源：

- https://open.goofish.com/doc/development/dev/server.html
- https://developer.alibaba.com/docs/api.htm?apiId=69130
- https://developer.alibaba.com/docs/api.htm?apiId=47401

结论：公开文档面向**闲鱼合作方 / ISV / 小程序**，不是普通卖家 App 的开放 SDK。

| 能力 | 官方接口 | 个人卖家控制台是否直接可用 |
| --- | --- | --- |
| 订单二次查询 | `alibaba.idle.isv.order.query` | 需 ISV 应用 + 卖家 accessToken |
| 已付款判定 | `order_status == 2` 且金额 > 0 | 同上；聊天卡片文本不算 |
| 虚拟发货确认 | `alibaba.idle.isv.goosefish.virtual.delivery` | 需卖家 accessToken |
| 正向/逆向消息 | `idle_autotrade_OrderStateSync` / `RefundSync` | 需消息订阅权限 |
| 商品发布 | `alibaba.idle.isv.item.publish` | 服务商商品发布，需受邀入驻 |
| 卖家 IM 收发 | 文档未提供正式 API | 不可作为官方路径 |

授权要点：淘宝开放平台 OAuth；卖家 token 可通过  
`https://open.api.goofish.com/authorize?response_type=token&client_id={appKey}&sp=xianyu&force_auth=true`  
获取，文档写明有效期 180 天。订单用户数据要求部署在聚石塔。

## 不要把网页端 appKey 当成官方凭证

浏览器或抓包里常见的 `appKey=34839810` 是闲鱼 PC/H5 网页客户端的公开标识，配合 Cookie、`_m_h5_tk` 和 mtop 签名使用。它不是淘宝开放平台发给合作方的应用 AppKey，也不能用来调用 `alibaba.idle.isv.*`。

本项目不把 `34839810` 写入 `GOOFISH_APP_KEY`，不实现该签名链路。

官方 AppKey 的来源：闲鱼三方开放平台申请应用，或淘宝开放平台「阿里生态开放 API / 闲鱼垂直行业」。卖家授权页的 `client_id` 必须是这个应用的 AppKey。

## 当前工程选择

1. 领域层只使用内部状态与 `MarketplaceAdapter`。
2. 官方状态码 `0–6` 只允许出现在 adapter 映射表，不进入领域对象字段名。
3. 未拿到合作方 AppKey / AppSecret / 卖家 accessToken 前，继续用 Fake Adapter。
4. 不复制 `zhinianboke/xianyu-auto-reply` 或其他逆向项目的 Cookie、WebSocket、签名或 RPA 实现。
5. 若长期拿不到正式 IM 接口，MVP 按规格降级：AI 后台 + 人工在闲鱼客户端点发送。
