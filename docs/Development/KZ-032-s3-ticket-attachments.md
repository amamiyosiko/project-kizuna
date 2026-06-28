# KZ-032 S3 Ticket Attachments

## Scope

本次只做 v0.3.2 目标：工作项附件上传与预览。

## API

- `POST /api/v1/attachments/tickets/{ticket_id}/presign`
- `POST /api/v1/attachments/tickets/{ticket_id}/confirm`
- `GET /api/v1/attachments/tickets/{ticket_id}`
- `GET /api/v1/attachments/{attachment_id}`

## Storage path

文件保存路径：

```text
attachments/{store_code}/{yyyy}/{mm}/{dd}/ticket-{ticket_id}-{ticket_no}/{uuid}.{ext}
```

## Frontend

`/workspace` 右侧详情区新增：

- S3 上传入口
- 附件列表
- 图片预览
- 打开 / 下载链接

## Migration

`20260628_0002_ticket_attachments.py` 给 `attachments` 增加 Ticket 关联字段。
