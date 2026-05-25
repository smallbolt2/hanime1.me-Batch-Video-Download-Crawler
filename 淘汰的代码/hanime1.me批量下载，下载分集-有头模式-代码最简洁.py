import os
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm

# ==================== 浏览器配置部分 ====================
# 创建Chrome浏览器的配置选项
options = uc.ChromeOptions()
#options.add_argument('--headless')  # 无头模式（注释掉了，所以会显示浏览器窗口）
options.add_argument('--disable-gpu')  # 禁用GPU加速
options.add_argument('--window-size=1920,1080')  # 设置浏览器窗口大小
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')  # 设置用户代理，模拟真实浏览器
# 创建Chrome浏览器实例，使用本地的chromedriver.exe驱动
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
    time.sleep(2)  # 等待2秒让页面加载完成
    soup = BeautifulSoup(driver.page_source, 'html.parser')  # 解析页面HTML内容
    links = []  # 存储找到的视频链接
    
    # 查找所有包含视频链接的a标签
    for a in soup.select('div.home-rows-videos-wrapper a[href*="/watch?v="]'):
        href = a.get('href')  # 获取链接地址
        # 验证链接是否有效且来自hanime1.me
        if href and href.startswith('https://hanime1.me/watch?v='):
            links.append(href)  # 添加到链接列表
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
    主函数：执行整个批量下载流程
    """
    # 设置要爬取的视频列表页面URL（这里是泡面番分类）
    list_url = "https://hanime1.me/search?genre=%E6%B3%A1%E9%BA%B5%E7%95%AA"
    save_dir = "videos"  # 设置保存视频的文件夹
    os.makedirs(save_dir, exist_ok=True)  # 创建保存文件夹（如果不存在）
    
    # 获取所有视频链接
    video_links = get_video_links(list_url)
    print(f"共找到{len(video_links)}个视频")
    
    # 遍历每个视频链接进行下载
    for idx, watch_url in enumerate(video_links):
        # 关闭除主窗口外的所有标签页，避免内存占用过多
        main_handle = driver.window_handles[0]  # 获取主窗口句柄
        for handle in driver.window_handles[1:]:  # 遍历其他窗口
            driver.switch_to.window(handle)  # 切换到该窗口
            driver.close()  # 关闭窗口
        driver.switch_to.window(main_handle)  # 切换回主窗口
        
        print(f"\n[{idx+1}/{len(video_links)}] 处理: {watch_url}")
        
        # ==================== 分集下载功能（已注释） ====================
        # 以下代码用于下载多集视频，目前被注释掉了
        # playlist_links = get_playlist_links(watch_url)  # 获取分集链接
        # playlist_links = list(dict.fromkeys(playlist_links))  # 去重
        # print(f"  共{len(playlist_links)}集")
        # for ep_idx, ep_url in enumerate(playlist_links):
        #     print(f"    [{ep_idx+1}/{len(playlist_links)}] 下载分集: {ep_url}")
        #     download_page_url = get_download_page_url(ep_url)  # 获取下载页面
        #     if not download_page_url:
        #         continue
        #     video_url, filename = get_real_video_url(download_page_url, quality="720p")  # 获取真实下载链接
        #     if not video_url:
        #         print("    未找到真实视频链接")
        #         continue
        #     save_path = os.path.join(save_dir, filename)  # 构建保存路径
        #     if os.path.exists(save_path):  # 检查文件是否已存在
        #         print("    已存在，跳过")
        #         continue
        #     print(f"    开始下载: {video_url}")
        #     download_video(video_url, save_path)  # 下载视频
        #     print("    下载完成")
        #     time.sleep(1)  # 延时1秒，防止请求过快被封
        
        # ==================== 单集下载功能（当前使用） ====================
        # 只下载主页面视频，不下载分集
        download_page_url = get_download_page_url(watch_url)  # 获取下载页面URL
        if not download_page_url:
            continue  # 如果获取失败，跳过当前视频
        
        video_url, filename = get_real_video_url(download_page_url, quality="720p")  # 获取真实视频链接
        if not video_url:
            print("    未找到真实视频链接")
            continue  # 如果获取失败，跳过当前视频
        
        save_path = os.path.join(save_dir, filename)  # 构建完整的保存路径
        if os.path.exists(save_path):  # 检查文件是否已经存在
            print("    已存在，跳过")
            continue  # 如果文件已存在，跳过下载
        
        print(f"    开始下载: {video_url}")
        download_video(video_url, save_path)  # 执行下载
        print("    下载完成")
        time.sleep(1)  # 延时1秒，防止请求频率过高被网站封禁

    # 下载完成后关闭浏览器
    driver.quit()
    print("全部下载完成")

# 程序入口点
if __name__ == "__main__":
    main()  # 运行主函数
