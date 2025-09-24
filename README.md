Nonebot-Plugin-QQgroup-Filedownloader
✨ 一个基于 NoneBot2 的插件，用于监听并下载QQ群上传的文件 ✨

# NoneBot FileDownloader 插件

这是一个 NoneBot2 插件，用于自动下载群聊中上传的文件。该插件支持配置下载间隔、重试机制、黑名单机制。

## 功能特性

- 自动下载群聊中上传的文件
- 可配置的下载延迟，避免频率限制
- 失败重试机制
- 完整的日志记录
- 支持配置黑名单


## 配置说明

### NoneBot 核心配置

通过修改 `config.py` 文件来配置NoneBot2核心和插件行为：

| 环境变量 | 说明 | 默认值 | 注意事项 |
|---------|------|--------|---------|
| `file_downloader_dir` | 文件下载目录 | `/app/test/downloads` | Docker 环境中使用 Linux 路径格式（正斜杠 `/`） |
| `file_downloader_min_wait_after_last_file` | 最后一个文件上传后等待的最小时间（秒） | `15` | - |
| `file_downloader_max_wait_after_last_file` | 最后一个文件上传后等待的最大时间（秒） | `30` | - |
| `file_downloader_min_wait_before_download` | 开始下载前等待的最小时间（秒） | `10` | - |
| `file_downloader_max_wait_before_download` | 开始下载前等待的最大时间（秒） | `5` | - |
| `file_downloader_retry_failed` | 失败重试开关 | `false` | - |
| `file_downloader_max_retries` | 最大重试次数 | `3` | - |
| `file_downloader_check_interval` | 检查下载队列的时间间隔（秒） | `60` | - |
| `qq_group_blacklist` | QQ群黑名单 | ['123456','1234567'] | - |


## Docker 环境特别说明

### 路径分隔符

- 在 `.env` 文件中，Docker 环境使用 **Linux 路径格式**（正斜杠 `/`）
- 例如：`FILE_DOWNLOADER_DIR=/app/test/downloads`
- 不要在 Docker 环境中使用 Windows 路径格式（反斜杠 `\`）

### 卷挂载

为了持久化保存下载的文件，`docker-compose.yml` 配置了两个卷挂载：

1. `.env` 文件：确保容器使用正确的配置
2. 下载目录：确保下载的文件可以在宿主机上访问

### 权限处理

插件会自动检测下载目录的写入权限，并在权限不足时尝试使用 `/tmp/file_downloader` 作为备选目录。

## 常见问题

### 1. 下载目录没有写权限

**问题**：`PermissionError: [Errno 13] Permission denied`

**解决方案**：
- 插件会自动尝试使用备选目录 `/tmp/file_downloader`
- 可以修改 `docker-compose.yml` 中的卷挂载配置，确保宿主机目录有正确的权限



### 修改插件配置

修改插件默认配置需要更新 `plugins/file_downloader/config.py` 文件。

## License

MIT
