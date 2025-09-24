from pydantic import BaseModel


class Config(BaseModel):
    # 文件下载目录，默认为插件目录下的downloads文件夹
    file_downloader_dir:str ="downloads"
    # 最后一个文件上传后等待的最小时间（秒），默认15秒
    file_downloader_min_wait_after_last_file : int = 15
    # 最后一个文件上传后等待的最大时间（秒），默认30秒
    file_downloader_max_wait_after_last_file: int = 30
    # 文件开始下载前的最小等待时间（秒），默认10秒
    file_downloader_min_wait_before_download: int = 10
    # 文件开始下载前的最大等待时间（秒），默认60秒
    file_downloader_max_wait_before_download: int = 60
    # 检查队列的时间间隔（秒），默认60秒
    file_downloader_check_interval:int = 60
    # 是否在下载失败时重新加入队列
    file_downloader_retry_failed:bool = False
    # 失败重试的最大次数
    file_downloader_max_retries: int = 3
    #QQ群黑名单, 在黑名单内的群不会自动下载, 格式:['123456','1234567']
    qq_group_blacklist:list = ['']