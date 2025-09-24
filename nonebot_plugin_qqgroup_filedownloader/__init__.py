import nonebot
from nonebot import on_notice, get_driver
from nonebot.adapters.onebot.v11 import NoticeEvent
from nonebot.adapters.onebot.v11 import Bot
from nonebot.plugin import PluginMetadata
from nonebot.log import logger
from nonebot import require
import asyncio
import random
import os
import time
import sys
from typing import List, Dict, Optional
import aiohttp
from pathlib import Path

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

from .config import Config


__plugin_meta__ = PluginMetadata(
    name="群文件下载",
    description="群文件下载 NoneBot 插件",
    usage="有群文件上传之后会自动下载",
    type="application",
    homepage="xxx",
    config=Config,
)


if hasattr(nonebot, "get_plugin_config"):
    plugin_config = nonebot.get_plugin_config(Config)
else:
    plugin_config = Config.parse_obj(nonebot.get_driver().config)


download_path = Path(plugin_config.file_downloader_dir)

if not download_path.exists():
    try:
        download_path.mkdir(parents=True)
    except PermissionError:
        download_path = store.get_data_dir("nonebot_plugin_anime_downloader")
        logger.warning(
            f"无法创建下载目录！请自行创建下载目录后重启 NoneBot. 本次下载目录为: {download_path}"
        )

# 打印运行环境信息,帮助调试
logger.info(f"Python版本: {sys.version}")
logger.info(f"运行路径: {os.getcwd()}")
logger.info(f"插件目录: {os.path.dirname(os.path.abspath(__file__))}")
logger.info(f"下载目录: {download_path}")

# 下载队列和状态管理
file_queue: List[Dict] = []
failed_files: Dict[str, int] = {}  # 记录失败的文件和重试次数
is_downloading: bool = False
last_file_time: float = 0.0
check_task: Optional[asyncio.Task] = None

# 确保下载目录在Docker环境中有写权限
try:
    # 测试写入权限
    test_file = os.path.join(download_path, ".write_test")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
    logger.info(f"下载目录有写权限: {download_path}")
except Exception as e:
    logger.error(f"下载目录没有写权限: {str(e)}")
    # 如果在Docker中权限不足,尝试使用/tmp作为备选目录
    fallback_dir = "/tmp/file_downloader"
    logger.warning(f"尝试使用备选下载目录: {fallback_dir}")
    try:
        os.makedirs(fallback_dir, exist_ok=True)
        # 测试备选目录的写入权限
        test_file = os.path.join(fallback_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        download_path = fallback_dir
        logger.info(f"已切换到备选下载目录: {download_path}")
    except Exception as e2:
        logger.error(f"备选目录也没有写权限: {str(e2)}")

# 监听群文件上传通知
group_file_upload = on_notice(priority=5)

@group_file_upload.handle()
async def handle_group_file_upload(bot: Bot, event: NoticeEvent):
    global last_file_time
    
    # 检查是否为群文件上传事件
    if event.notice_type != "group_upload":
        return
    if str(event.group_id) in plugin_config.qq_group_blacklist:
        logger.info(f"该群号在黑名单内: {event.group_id}")
        return
    # 获取文件信息
    file_info = event.file
    
    try:
        # file_info是pydantic模型,直接使用属性访问方式获取信息
        file_data = {
            "file_id": file_info.id,
            "file_name": file_info.name,
            "file_size": file_info.size,
            "group_id": event.group_id,
            "upload_time": time.time()
        }
    except Exception as e:
        logger.error(f"获取文件信息失败: {str(e)}")
        return
    
    # 添加到下载队列
    file_queue.append(file_data)
    last_file_time = time.time()
    
    logger.info(f"检测到新文件: {file_data['file_name']} (大小: {file_data['file_size']} bytes) 来自群: {file_data['group_id']}")
    
    # 启动检查任务（如果未启动）
    global check_task
    if check_task is None or check_task.done():
        check_task = asyncio.create_task(check_download_queue(bot))

async def check_download_queue(bot: Bot):
    """检查下载队列,在适当的时机开始下载"""
    global last_file_time
    
    while True:
        # 如果队列为空,退出循环
        if not file_queue:
            break
            
        # 检查是否距离最后一个文件上传已经过了足够时间
        current_time = time.time()
        time_since_last_file = current_time - last_file_time
        
        # 如果距离最后一个文件上传不足配置的时间,继续等待
        wait_time = random.randint(plugin_config.file_downloader_min_wait_after_last_file, 
                                  plugin_config.file_downloader_max_wait_after_last_file)
        if time_since_last_file < wait_time:
            # 等待一段时间后再次检查
            await asyncio.sleep(plugin_config.file_downloader_check_interval)
            continue
        
        # 开始下载队列中的文件
        await start_download_files(bot)
        break

async def start_download_files(bot: Bot):
    """按顺序下载队列中的文件"""
    global is_downloading
    if is_downloading:
        return
        
    is_downloading = True
    try:
        while file_queue:
            # 获取队列中的第一个文件
            file_data = file_queue.pop(0)
            file_key = f"{file_data['group_id']}_{file_data['file_id']}"
            
            # 随机等待配置的时间
            wait_time = random.randint(plugin_config.file_downloader_min_wait_before_download, 
                                     plugin_config.file_downloader_max_wait_before_download)
            logger.info(f"等待{wait_time}秒后开始下载: {file_data['file_name']}")
            await asyncio.sleep(wait_time)
            
            # 下载文件
            success = await download_file(bot, file_data)
            
            if success:
                logger.info(f"文件下载成功: {file_data['file_name']}")
                # 从失败记录中移除
                if file_key in failed_files:
                    del failed_files[file_key]
            else:
                logger.error(f"文件下载失败: {file_data['file_name']}")
                
                # 如果配置了重试,并且重试次数未超过限制,重新加入队列
                if plugin_config.file_downloader_retry_failed:
                    failed_files.setdefault(file_key, 0)
                    failed_files[file_key] += 1
                    
                    if failed_files[file_key] <= plugin_config.file_downloader_max_retries:
                        logger.info(f"准备重试下载文件 {file_data['file_name']},第{failed_files[file_key]}次重试")
                        file_queue.append(file_data)
                    else:
                        logger.error(f"文件 {file_data['file_name']} 已达到最大重试次数,不再重试")
    finally:
        is_downloading = False

async def download_file(bot: Bot, file_data: Dict) -> bool:
    """下载单个文件"""
    try:
        # 检查aiohttp模块是否可用
        if aiohttp is None:
            logger.error(f"aiohttp模块缺失,无法下载文件: {file_data['file_name']}")
            return False
        
        # 使用OneBot API获取文件下载链接
        file_url = await bot.call_api(
            "get_group_file_url",
            group_id=file_data["group_id"],
            file_id=file_data["file_id"]
        )
        
        # 确保url字段存在
        if "url" not in file_url:
            logger.error(f"无法获取文件URL: {file_data['file_name']}")
            return False
        
        # 构建保存路径
        save_path = os.path.join(download_path, file_data["file_name"])
        
        # 使用aiohttp下载文件
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url["url"]) as response:
                if response.status == 200:
                    with open(save_path, 'wb') as f:
                        f.write(await response.read())
                    logger.info(f"文件已保存到: {save_path}")
                    return True
                else:
                    logger.error(f"下载失败,HTTP状态码: {response.status}, 文件: {file_data['file_name']}")
                    return False
    except Exception as e:
        logger.error(f"下载文件时发生错误: {str(e)}, 文件: {file_data['file_name']}")
        return False

# 在插件加载时初始化
@get_driver().on_startup
async def startup():
    global download_path
    # 确保下载目录存在
    if not os.path.exists(download_path):
        try:
            os.makedirs(download_path)
            logger.info(f"创建下载目录: {download_path}")
        except Exception as e:
            logger.error(f"创建下载目录失败: {str(e)}")
    else:
        logger.info(f"下载目录已存在: {download_path}")
    
    # 打印配置信息
    logger.info(f"文件下载插件已启动")
    logger.info(f"配置参数: 最后文件等待时间范围 {plugin_config.file_downloader_min_wait_after_last_file}-{plugin_config.file_downloader_max_wait_after_last_file}秒")
    logger.info(f"配置参数: 下载前等待时间范围 {plugin_config.file_downloader_min_wait_before_download}-{plugin_config.file_downloader_max_wait_before_download}秒")
    logger.info(f"配置参数: 失败重试 {'开启' if plugin_config.file_downloader_retry_failed else '关闭'},最大重试次数 {plugin_config.file_downloader_max_retries}")
    logger.info(f"配置参数: 检查队列间隔 {plugin_config.file_downloader_check_interval}秒")
    logger.info(f"配置参数: QQ群黑名单 {plugin_config.qq_group_blacklist}")
    
    # 检查运行环境
    logger.info(f"操作系统: {sys.platform}")
    logger.info(f"用户ID: {os.getuid() if hasattr(os, 'getuid') else 'N/A'}")
    logger.info(f"组ID: {os.getgid() if hasattr(os, 'getgid') else 'N/A'}")

# 在插件关闭时清理
@get_driver().on_shutdown
async def shutdown():
    global check_task
    if check_task and not check_task.done():
        check_task.cancel()
    logger.info("文件下载插件已关闭")
