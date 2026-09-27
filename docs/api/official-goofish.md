# 官方 Goofish / 闲鱼接口备忘

仅记录公开文档中的名称、用途与状态映射，供后续 Official Adapter 做 contract test。不包含非公开协议。

## 环境

| 项 | 值 |
| --- | --- |
| TOP 正式 | `https://gw.api.taobao.com/router/rest` |
| TOP 预发 | `https://pre-gw.api.taobao.com/top/router/rest` |
| 卖家授权 | `https://open.api.goofish.com/authorize?response_type=token&client_id={appKey}&sp=xianyu&force_auth=true` |

发货、关单、退款类接口使用**卖家** accessToken。创单和部分用户信息使用**当前登录用户** token。

## 订单状态（官方数字 → 领域枚举）

| 官方 `order_status` | 含义 | 领域 `PlatformOrderStatus` |
| --- | --- | --- |
| 0 | 未知 | `UNKNOWN` |
| 1 | 已创建 / 待付款 | `CREATED` |
| 2 | 已付款 / 待发货 | `PAID` |
| 3 | 已发货 | `SHIPPED` |
| 4 | 交易成功 | `SUCCESS` |
| 5 | 已退款 | `REFUNDED` |
| 6 | 交易关闭 | `CLOSED` |

只有查询结果为 `PAID` 且实付金额 > 0 才能进入 `PAID_VERIFIED`。`PAYMENT_REPORTED`（买家自称已付款或聊天卡片）只是线索。

## 关键方法

- `alibaba.idle.isv.order.query` — 入参 `biz_order_id`；出参含 `payment`（分）、`pay_time`、`item` 信息
- `alibaba.idle.isv.goosefish.virtual.delivery` — 入参 `biz_order_id`
- `alibaba.idle.isv.refund.query` / `alibaba.idle.isv.order.dealrefund` — v1 只读查询，处理转人工
- `alibaba.idle.isv.item.publish` — 服务商发布；v1 发布仍须人工审批
- 消息 topic：`idle_autotrade_OrderStateSync`、`idle_autotrade_RefundSync`

## 明确缺失

公开文档没有卖家 IM 会话收发、没有个人 Cookie 会话 API。
