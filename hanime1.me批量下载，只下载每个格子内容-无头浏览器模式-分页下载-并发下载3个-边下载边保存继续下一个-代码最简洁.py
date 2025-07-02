import os
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 浏览器配置部分 ====================
# 创建Chrome浏览器的配置选项
options = uc.ChromeOptions()

# 设置为无头模式（不显示浏览器窗口）
options.add_argument('--headless')  # 无头模式
options.add_argument('--disable-gpu')  # 禁用GPU加速
options.add_argument('--window-size=1920,1080')  # 设置浏览器窗口大小

# 添加用户代理和语言设置，防止cloudflare弹验证
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
options.add_argument('--accept-language=en-US,en;q=0.9')

# 创建Chrome浏览器实例，使用本地的chromedriver.exe驱动
# 注意：chromedriver.exe路径需根据实际情况修改
driver = uc.Chrome(options=options, driver_executable_path=r"E:\hanime1.me视频批量下载\chromedriver.exe")

# ==================== 核心功能函数 ====================

def get_video_links(list_url):
    """
    从视频列表页面获取所有视频的链接
    参数:
        list_url: 视频列表页面的URL
    返回:
        links: 包含所有视频链接的列表
    """
    driver.get(list_url)  # 打开视频列表页面
    time.sleep(2)  # 等待页面加载
    soup = BeautifulSoup(driver.page_source, 'html.parser')  # 解析页面HTML
    links = []  # 存储视频链接
    # 查找所有视频格子的a标签
    for a in soup.select('div.home-rows-videos-wrapper a[href*="/watch?v="]'):
        href = a.get('href')  # 获取链接
        if href and href.startswith('https://hanime1.me/watch?v='):
            links.append(href)  # 添加到列表
    return links

def get_download_page_url(watch_url):
    """
    从视频观看页面获取下载页面的URL
    参数:
        watch_url: 视频观看页面的URL
    返回:
        download_page_url: 下载页面的URL，如果失败返回None
    """
    driver.get(watch_url)  # 打开视频观看页面
    time.sleep(2)  # 等待页面加载
    try:
        # 记录当前所有打开的窗口
        original_windows = driver.window_handles
        # 找到页面上的下载按钮并点击
        download_btn = driver.find_element(By.ID, "downloadBtn")
        download_btn.click()
        time.sleep(2)  # 等待新窗口打开
        # 获取点击后的所有窗口
        new_windows = driver.window_handles
        # 找到新打开的窗口（下载页面）
        for handle in new_windows:
            if handle not in original_windows:
                driver.switch_to.window(handle)  # 切换到新窗口
                download_page_url = driver.current_url  # 获取新窗口的URL
                return download_page_url
        # 如果没有新窗口，返回当前页面的URL
        return driver.current_url
    except Exception as e:
        print(f"未找到下载按钮: {watch_url}，错误: {e}")
        return None

import re

def sanitize_filename(filename):
    """
    清理文件名，移除Windows文件系统中不允许的字符
    参数:
        filename: 原始文件名
    返回:
        清理后的安全文件名
    """
    # 定义Windows不允许的字符
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    # 替换为下划线或移除
    filename = re.sub(invalid_chars, '_', filename)
    # 移除连续的下划线
    filename = re.sub(r'_+', '_', filename)
    # 移除开头和结尾的下划线
    filename = filename.strip('_')
    return filename

def get_real_video_url(download_page_url, quality="720p"):
    """
    从下载页面获取真实的视频下载链接
    参数:
        download_page_url: 下载页面的URL
        quality: 视频质量，默认720p
    返回:
        video_url: 真实的视频下载链接
        filename: 视频文件名
    """
    driver.get(download_page_url)  # 打开下载页面
    time.sleep(2)  # 等待页面加载
    soup = BeautifulSoup(driver.page_source, 'html.parser')  # 解析页面内容
    # 遍历页面中的表格行，查找包含指定画质的行
    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td")  # 获取表格行中的所有单元格
        if len(tds) >= 5 and quality in tds[1].get_text():
            a_tag = tds[4].find("a")  # 在第5个单元格中查找下载链接
            if a_tag and a_tag.has_attr("data-url"):
                video_url = a_tag["data-url"]  # 获取真实的视频URL
                video_name = a_tag.get("download", "")  # 获取视频名称
                file_part = video_url.split("/")[-1].split("?")[0]  # 提取原始文件名
                filename = f"{video_name}-{file_part}"  # 组合新文件名
                # 清理文件名
                filename = sanitize_filename(filename)
                return video_url, filename
    return None, None

def download_video(video_url, save_path):
    """
    下载视频文件到指定路径
    参数:
        video_url: 视频的下载链接
        save_path: 保存文件的路径
    """
    try:
        # 发送GET请求下载视频，stream=True表示流式下载
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()  # 检查请求是否成功
            total = int(r.headers.get('content-length', 0))  # 获取文件总大小
            # 打开文件并显示下载进度条
            with open(save_path, 'wb') as f, tqdm(
                desc=save_path,  # 进度条描述
                total=total,  # 总大小
                unit='iB',  # 单位
                unit_scale=True,  # 自动缩放单位
                unit_divisor=1024,  # 除数
            ) as bar:
                # 分块下载文件
                for chunk in r.iter_content(chunk_size=1024):
                    size = f.write(chunk)  # 写入文件
                    bar.update(size)  # 更新进度条
    except Exception as e:
        print(f"下载失败: {video_url}，错误: {e}")

def get_playlist_links(watch_url):
    """
    获取视频的分集链接（如果有多集的话）
    参数:
        watch_url: 视频观看页面的URL
    返回:
        playlist: 包含所有分集链接的列表
    """
    driver.get(watch_url)  # 打开视频页面
    time.sleep(2)  # 等待页面加载
    soup = BeautifulSoup(driver.page_source, 'html.parser')  # 解析页面
    playlist = []
    # 查找播放列表中的所有分集链接
    for a in soup.select('div#playlist-scroll a.overlay'):
        href = a.get('href')
        if href and href.startswith('https://hanime1.me/watch?v='):
            playlist.append(href)
    # 如果没有找到分集，就把当前页面作为唯一的一集
    if not playlist:
        playlist.append(watch_url)
    return playlist

def main():
    """
    主函数：自动遍历所有分页，收集所有视频链接，并发下载视频
    """
    # ==================== 自动遍历所有分页，收集所有视频链接 ====================
    all_video_links = []  # 用于存储所有页面的视频链接
    seen_links = set()    # 用于去重，防止重复
    page = 1
    while True:
        # 构造分页URL，第一页和后续页URL格式不同
        if page == 1:
            list_url = "https://hanime1.me/search?query=&type=&genre=%E8%A3%8F%E7%95%AA&sort=&year=2024&month="
        else:
            list_url = f"https://hanime1.me/search?genre=%E8%A3%8F%E7%95%AA&year=2024&page={page}"
        print(f"正在处理第{page}页: {list_url}")
        video_links = get_video_links(list_url)
        # 过滤掉已经收集过的链接
        new_links = [link for link in video_links if link not in seen_links]
        if not new_links:
            print("没有新的视频链接，分页遍历结束。")
            break  # 没有新的视频，跳出循环
        all_video_links.extend(new_links)
        seen_links.update(new_links)
        print(f"  本页新增{len(new_links)}个视频，总计{len(all_video_links)}个视频")
        page += 1
    print(f"共收集到{len(all_video_links)}个视频链接")

    # ==================== 边获取边下载 ====================
    save_dir = "videos"  # 设置保存视频的文件夹
    os.makedirs(save_dir, exist_ok=True)  # 创建保存文件夹（如果不存在）

    print("边获取边下载，每次最多3个同时下载...")

    # 定义一个包装函数，线程池会用它来执行下载任务
    def download_task_wrapper(video_url, save_path):
        """
        这个函数就是用来下载一个视频的。
        参数：
            video_url: 这个视频的下载链接
            save_path: 这个视频要保存到本地的文件路径
        """
        print(f"开始下载: {save_path}")  # 打印开始下载的信息
        download_video(video_url, save_path)  # 调用前面定义好的下载函数，真正去下载
        print(f"下载完成: {save_path}")  # 打印下载完成的信息

    # 创建一个线程池，最多允许3个线程同时工作（即最多同时下载3个视频）
    # 线程池的作用就是可以让多个任务（这里是下载视频）同时进行，提高效率
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []  # 用于保存所有future对象，便于后续等待所有任务完成
        # 下面这个循环是依次处理每一个视频链接
        # 从第69个视频开始处理（因为前68个已经处理过了）
        # 注意：这里的索引是从0开始的，所以start设置第69个视频的----可以删除
        #for idx, watch_url in enumerate(all_video_links[44:], start=44):
        for idx, watch_url in enumerate(all_video_links):
            print(f"\n[编号{idx}] 处理: {watch_url}")
            # 关闭除主窗口外的所有标签页，避免内存占用过多
            main_handle = driver.window_handles[0]  # 获取主窗口句柄
            for handle in driver.window_handles[1:]:  # 遍历其他窗口
                driver.switch_to.window(handle)  # 切换到该窗口
                driver.close()  # 关闭窗口
            driver.switch_to.window(main_handle)  # 切换回主窗口

            # 获取下载页面URL，这一步是用浏览器自动化打开视频页面，点击下载按钮，拿到下载页面的真实地址
            download_page_url = get_download_page_url(watch_url)
            if not download_page_url:
                print("  获取下载页面失败，跳过")
                continue  # 如果没拿到下载页面，跳过这个视频
            # 获取真实视频链接和文件名，这一步是解析下载页面，找到真正的视频文件下载地址
            video_url, filename = get_real_video_url(download_page_url, quality="720p")
            if not video_url:
                print("  未找到真实视频链接，跳过")
                continue  # 如果没拿到视频链接，跳过
            save_path = os.path.join(save_dir, filename)  # 拼出保存到本地的完整路径
            if os.path.exists(save_path):
                print("  已存在，跳过")
                continue  # 如果文件已经存在，跳过

            # 只要获取到一个下载链接，就立刻提交到线程池下载
            # executor.submit 会安排download_task_wrapper函数在线程池中执行
            future = executor.submit(download_task_wrapper, video_url, save_path)
            futures.append(future)  # 把future对象保存起来，后面用来等待所有任务完成

        # 等待所有下载任务完成
        # as_completed会在每个任务完成时返回它的future对象
        # 这样可以一边下载一边处理结果，不用等所有任务都结束
        for future in as_completed(futures):
            try:
                future.result()  # 这行代码会等这个任务真正完成，如果有异常会抛出来
            except Exception as exc:
                print(f"下载失败: {exc}")  # 如果下载出错，打印错误信息

    driver.quit()  # 关闭浏览器，释放资源
    print("全部下载完成")  # 打印全部完成信息

# 程序入口点
if __name__ == "__main__":
    main()  # 运行主函数
