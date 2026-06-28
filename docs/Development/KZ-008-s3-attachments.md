# KZ-008 S3 文件上传

版本：v0.1.4

## 目标

在 Customer Workspace 中支持为会话上传客服相关图片和附件，文件保存到 Amazon S3，数据库只保存附件元数据和 object_key。

## 本版本范围

- 新增 `attachments` 数据表。
- 新增 S3 Presigned PUT URL 接口。
- 新增附件上传确认接口。
- 新增会话附件列表接口。
- Workspace 支持选择文件、上传到 S3、保存附件记录、展示附件列表。

## API

### POST /api/v1/attachments/presign

生成临时上传地址。

```json
{
  "conversation_id": 1,
  "file_name": "damage.jpg",
  "content_type": "image/jpeg",
  "file_size": 102400
}
```

### POST /api/v1/attachments/confirm

前端 PUT 到 S3 成功后，调用该接口保存数据库记录。

### GET /api/v1/attachments/conversation/{conversation_id}

获取某个会话的附件列表。

## S3 Object Key 规则

```text
attachments/{store_code}/{yyyy}/{mm}/{dd}/conversation-{conversation_id}/{uuid}.{ext}
```

示例：

```text
attachments/JP01/2026/06/28/conversation-12/0af1d2.jpg
```

## 环境变量

```env
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=project-kizuna-files
S3_UPLOAD_EXPIRES_SECONDS=900
```

## S3 Bucket CORS 示例

开发阶段可先配置：

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT", "GET", "HEAD"],
    "AllowedOrigins": ["http://localhost:3000"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

正式上线后需要把 AllowedOrigins 改为正式域名。

## IAM 最小权限建议

只允许访问指定 Bucket 下的附件目录：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::project-kizuna-files/attachments/*"
    }
  ]
}
```

## 设计原则

- 图片和附件不经过 EC2 中转，降低服务器压力。
- 数据库不保存完整 URL，只保存 bucket 和 object_key，方便未来切换 CDN 或 Bucket。
- V1 先做附件存档和客服查看；图片识别、OCR、AI 分析放到后续版本。
