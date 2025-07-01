import os
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm

# 配置 Selenium
options = uc.ChromeOptions()
#options.add_argument('--headless')  # 无头模式
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
driver = uc.Chrome(options=options, driver_executable_path=r"E:\hanime1.me视频批量下载\chromedriver.exe")
    # 使用本地的chromedriver.exe
    #service = Service(r'C:\Users\Administrator\Desktop\批量下载\chromedriver.exe')
    #driver = webdriver.Chrome(service=service, options=chrome_options)
    #return driver


def get_video_links(list_url):
    driver.get(list_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = []
    for a in soup.select('div.home-rows-videos-wrapper a[href*="/watch?v="]'):
        href = a.get('href')
        if href and href.startswith('https://hanime1.me/watch?v='):
            links.append(href)
    return links

def get_download_page_url(watch_url):
    driver.get(watch_url)
    time.sleep(2)
    try:
        # 记录当前所有窗口
        original_windows = driver.window_handles
        # 找到下载按钮并点击
        download_btn = driver.find_element(By.ID, "downloadBtn")
        download_btn.click()
        time.sleep(2)
        # 新窗口出现
        new_windows = driver.window_handles
        # 找到新开的窗口
        for handle in new_windows:
            if handle not in original_windows:
                driver.switch_to.window(handle)
                download_page_url = driver.current_url
                return download_page_url
        # 如果没新窗口，返回当前url
        return driver.current_url
    except Exception as e:
        print(f"未找到下载按钮: {watch_url}，错误: {e}")
        return None

def get_real_video_url(download_page_url, quality="720p"):
    driver.get(download_page_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    # 遍历所有行，查找包含目标画质的行
    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td")
        if len(tds) >= 5 and quality in tds[1].get_text():
            a_tag = tds[4].find("a")
            if a_tag and a_tag.has_attr("data-url"):
                video_url = a_tag["data-url"]
                # 获取视频名
                video_name = a_tag.get("download", "")
                # 获取原始文件名
                file_part = video_url.split("/")[-1].split("?")[0]
                # 拼接新文件名
                filename = f"{video_name}-{file_part}"
                return video_url, filename
    return None, None

def download_video(video_url, save_path):
    try:
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            with open(save_path, 'wb') as f, tqdm(
                desc=save_path,
                total=total,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in r.iter_content(chunk_size=1024):
                    size = f.write(chunk)
                    bar.update(size)
    except Exception as e:
        print(f"下载失败: {video_url}，错误: {e}")

def get_playlist_links(watch_url):
    driver.get(watch_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    playlist = []
    for a in soup.select('div#playlist-scroll a.overlay'):
        href = a.get('href')
        if href and href.startswith('https://hanime1.me/watch?v='):
            playlist.append(href)
    # 如果没有分集，返回当前页
    if not playlist:
        playlist.append(watch_url)
    return playlist

def main():
    list_url = "https://hanime1.me/search?genre=%E6%B3%A1%E9%BA%B5%E7%95%AA"
    save_dir = "videos"
    os.makedirs(save_dir, exist_ok=True)
    video_links = get_video_links(list_url)
    print(f"共找到{len(video_links)}个视频")
    for idx, watch_url in enumerate(video_links):
        # 关闭除第一个外的所有标签页
        main_handle = driver.window_handles[0]
        for handle in driver.window_handles[1:]:
            driver.switch_to.window(handle)
            driver.close()
        driver.switch_to.window(main_handle)
        # 下面是原有逻辑
        print(f"\n[{idx+1}/{len(video_links)}] 处理: {watch_url}")
        # playlist_links = get_playlist_links(watch_url)
        # playlist_links = list(dict.fromkeys(playlist_links))
        # print(f"  共{len(playlist_links)}集")
        # for ep_idx, ep_url in enumerate(playlist_links):
        #     print(f"    [{ep_idx+1}/{len(playlist_links)}] 下载分集: {ep_url}")
        #     download_page_url = get_download_page_url(ep_url)
        #     if not download_page_url:
        #         continue
        #     video_url, filename = get_real_video_url(download_page_url, quality="720p")
        #     if not video_url:
        #         print("    未找到真实视频链接")
        #         continue
        #     save_path = os.path.join(save_dir, filename)
        #     if os.path.exists(save_path):
        #         print("    已存在，跳过")
        #         continue
        #     print(f"    开始下载: {video_url}")
        #     download_video(video_url, save_path)
        #     print("    下载完成")
        #     time.sleep(1)  # 防止过快被封
        # 只下载主页面
        download_page_url = get_download_page_url(watch_url)
        if not download_page_url:
            continue
        video_url, filename = get_real_video_url(download_page_url, quality="720p")
        if not video_url:
            print("    未找到真实视频链接")
            continue
        save_path = os.path.join(save_dir, filename)
        if os.path.exists(save_path):
            print("    已存在，跳过")
            continue
        print(f"    开始下载: {video_url}")
        download_video(video_url, save_path)
        print("    下载完成")
        time.sleep(1)  # 防止过快被封

    driver.quit()
    print("全部下载完成")

if __name__ == "__main__":
    main()
