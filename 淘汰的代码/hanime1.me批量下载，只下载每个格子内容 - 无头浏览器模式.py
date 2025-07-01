import os
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from tqdm import tqdm

# 配置 Selenium
user_data_dir = r"E:\hanime1.me视频批量下载\chrome_profile"
options = uc.ChromeOptions()
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument('--headless=new')  # 保持无头模式
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')
# 添加反检测参数
options.add_argument('--disable-browser-side-navigation')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')
options.add_argument('--disable-setuid-sandbox')
options.add_argument('--disable-webgl')
options.add_argument('--disable-infobars')
options.add_argument('--disable-extensions')
options.add_argument('--disable-popup-blocking')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--log-level=3')  # 减少日志输出

# 添加用户代理和语言设置
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
options.add_argument('--accept-language=en-US,en;q=0.9')

driver = uc.Chrome(options=options, driver_executable_path=r"E:\hanime1.me视频批量下载\chromedriver.exe")

def bypass_cloudflare(url):
    """专门处理Cloudflare验证的函数"""
    print(f"访问初始URL: {url}")
    driver.get(url)
    
    # 检查Cloudflare验证
    for attempt in range(5):  # 最多尝试5次
        time.sleep(5)  # 等待页面加载
        
        # 检查是否出现Cloudflare验证
        if "challenge" in driver.page_source.lower():
            print(f"检测到Cloudflare验证 (尝试 {attempt+1}/5)")
            
            # 尝试提交验证表单（如果存在）
            try:
                submit_btn = driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Verify')]")
                if submit_btn:
                    print("尝试自动提交验证...")
                    submit_btn.click()
                    time.sleep(10)  # 等待验证结果
            except:
                pass
            
            # 检查验证是否通过
            if "challenge" not in driver.page_source.lower():
                print("验证通过!")
                return True
            else:
                print("验证未通过，等待中...")
                time.sleep(15)  # 等待更长时间
        else:
            print("未检测到验证，继续...")
            return True
    
    print("无法通过Cloudflare验证")
    return False

def get_video_links(list_url):
    """获取视频链接，处理初始验证"""
    if not bypass_cloudflare(list_url):
        print("无法获取视频列表，跳过")
        return []
    
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = []
    for a in soup.select('div.home-rows-videos-wrapper a[href*="/watch?v="]'):
        href = a.get('href')
        if href and href.startswith('https://hanime1.me/watch?v='):
            links.append(href)
    return links

def get_download_page_url(watch_url):
    for attempt in range(3):  # 添加重试机制
        try:
            driver.get(watch_url)
            # 使用显式等待代替固定等待
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "downloadBtn"))
            )
            
            original_windows = driver.window_handles
            download_btn = driver.find_element(By.ID, "downloadBtn")
            download_btn.click()
            
            # 显式等待新窗口出现
            WebDriverWait(driver, 10).until(
                lambda d: len(d.window_handles) > len(original_windows)
            )
            
            new_windows = driver.window_handles
            for handle in new_windows:
                if handle not in original_windows:
                    driver.switch_to.window(handle)
                    download_page_url = driver.current_url
                    return download_page_url
            return driver.current_url
        except Exception as e:
            print(f"尝试 {attempt+1}/3 失败: {e}")
            if "cloudflare" in driver.page_source.lower():
                print("检测到Cloudflare验证，等待中...")
                time.sleep(15)  # 给验证留出时间
    return None

def get_real_video_url(download_page_url, quality="720p"):
    driver.get(download_page_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td")
        if len(tds) >= 5 and quality in tds[1].get_text():
            a_tag = tds[4].find("a")
            if a_tag and a_tag.has_attr("data-url"):
                video_url = a_tag["data-url"]
                video_name = a_tag.get("download", "")
                file_part = video_url.split("/")[-1].split("?")[0]
                filename = f"{video_name}-{file_part}"
                return video_url, filename
    return None, None

def get_cookies_dict(driver):
    cookies = driver.get_cookies()
    cookies_dict = {}
    for cookie in cookies:
        cookies_dict[cookie['name']] = cookie['value']
    return cookies_dict

def download_video(video_url, save_path, cookies):
    try:
        with requests.get(video_url, stream=True, cookies=cookies) as r:
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

def main():
    list_url = "https://hanime1.me/search?query=&type=&genre=%E8%A3%8F%E7%95%AA&sort=&year=2024&month="
    save_dir = "videos"
    os.makedirs(save_dir, exist_ok=True)
    
    # 初始访问处理
    video_links = get_video_links(list_url)
    
    if not video_links:
        print("无法获取视频列表，退出程序")
        driver.quit()
        return
    
    print(f"共找到{len(video_links)}个视频")
    
    for idx, watch_url in enumerate(video_links):
        # 添加Cloudflare检测
        if "challenge" in driver.page_source.lower():
            print("检测到验证页面，等待中...")
            time.sleep(20)  # 给验证更多时间
        
        main_handle = driver.window_handles[0]
        for handle in driver.window_handles[1:]:
            driver.switch_to.window(handle)
            driver.close()
        driver.switch_to.window(main_handle)
        
        print(f"\n[{idx+1}/{len(video_links)}] 处理: {watch_url}")
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
        cookies = get_cookies_dict(driver)
        download_video(video_url, save_path, cookies)
        print("    下载完成")
        time.sleep(1)

    driver.quit()
    print("全部下载完成")

if __name__ == "__main__":
    driver.get("https://hanime1.me/search?query=&type=&genre=%E8%A3%8F%E7%95%AA&sort=&year=2024&month=")
    input("请在弹出的浏览器窗口手动通过Cloudflare验证，验证通过后按回车继续...")
    print(driver.page_source[:500])  # 打印部分源码，确认是否为正常页面
    main()