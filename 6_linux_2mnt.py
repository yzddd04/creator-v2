import asyncio
from playwright.async_api import async_playwright
import time
from datetime import datetime, timezone, timedelta
import re
import os, sys
from pymongo import MongoClient
import pymongo
import psutil
import threading
import subprocess
import platform
import gc
from collections import Counter
from collections import defaultdict
import traceback
import pytz

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

# Unicode symbols for modern UI
CHECK_MARK = '✅'
CROSS_MARK = '❌'
WARNING = '⚠️'
INFO = 'ℹ️'
CLOCK = '⏰'
ROCKET = '🚀'
COMPUTER = '💻'
GLOBE = '🌐'
USER_ICON = '👤'
SUN = '☀️'
MOON = '🌙'
STAR = '⭐'
PLATFORM_ICONS = {
    'instagram': '📸',
    'tiktok': '🎵'
}

# WIB Timezone
WIB_TZ = pytz.timezone('Asia/Jakarta')

# Cek dan install playwright package jika belum ada
try:
    import playwright
except ImportError:
    print("Playwright belum terinstall. Menginstall playwright...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    import playwright

# Cek dan install browser Playwright jika belum ada
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        pass
except Exception:
    print("Menginstall browser Playwright...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install"])

# --- FUNGSI UTILITAS RAM DAN FILE SIZE ---
def get_chrome_processes():
    """Kembalikan list proses chrome/chromium/msedge/playwright yang aktif."""
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            name = proc.info['name']
            if name and any(x in name.lower() for x in ['chrome', 'chromium', 'msedge', 'playwright']):
                procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs

def get_chrome_memory_usage():
    """Mengembalikan total penggunaan RAM (MB) oleh semua proses chrome/chromium/msedge/playwright."""
    procs = get_chrome_processes()
    if not procs:
        return 0.0
    total = sum(proc.info['memory_info'].rss for proc in procs)
    return round(total / 1024 / 1024, 2)  # dalam MB

def get_python_memory_usage():
    """Mengembalikan penggunaan RAM (MB) oleh proses Python ini."""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)

def get_code_file_size():
    try:
        size = os.path.getsize(__file__)
        return round(size / 1024, 2)
    except Exception:
        return 'N/A'

def clean_and_convert_to_int(value_str):
    if value_str is None or value_str == "N/A":
        return None
    try:
        return int(re.sub(r'[^\d]', '', value_str))
    except (ValueError, TypeError):
        return None

def clear_screen():
    os.system('clear')

def get_next_run_time():
    """Hitung waktu sampai 2 menit berikutnya"""
    now = datetime.now(WIB_TZ)
    # Target adalah 2 menit dari sekarang
    target_time = now + timedelta(minutes=2)
    return target_time

def get_time_until_next_run():
    """Hitung berapa lama lagi sampai 2 menit berikutnya"""
    next_run = get_next_run_time()
    now = datetime.now(WIB_TZ)
    time_diff = next_run - now
    
    hours = int(time_diff.total_seconds() // 3600)
    minutes = int((time_diff.total_seconds() % 3600) // 60)
    seconds = int(time_diff.total_seconds() % 60)
    
    return hours, minutes, seconds

def print_header():
    """Print header yang modern dan menarik"""
    now = datetime.now(WIB_TZ)
    next_run = get_next_run_time()
    hours, minutes, seconds = get_time_until_next_run()
    
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{MAGENTA}🤖 CREATOR WEB MONITORING BOT 🤖{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{INFO} {BLUE}Instagram & TikTok Followers Monitor (Every 2 Minutes){RESET}")
    print(f"{CLOCK} {BLUE}Current Time (WIB): {now.strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{SUN} {BLUE}Next Run: {next_run.strftime('%Y-%m-%d %H:%M:%S')} WIB{RESET}")
    print(f"{STAR} {BLUE}Time Until Next Run: {hours:02d}:{minutes:02d}:{seconds:02d}{RESET}")
    print(f"{INFO} {BLUE}Today's Date: {now.strftime('%A, %d %B %Y')}{RESET}")
    
    # Tampilkan informasi waktu yang tersisa dalam format yang mudah dibaca
    if hours >= 24:
        days = hours // 24
        remaining_hours = hours % 24
        print(f"{CLOCK} {BLUE}Sleep Duration: {days} days, {remaining_hours} hours, {minutes:02d} minutes{RESET}")
    else:
        print(f"{CLOCK} {BLUE}Sleep Duration: {hours} hours, {minutes:02d} minutes{RESET}")
    
    # Cek status monitoring hari ini
    today = datetime.now(WIB_TZ).strftime('%Y-%m-%d')
    today_stats = list(stats_collection.find({'date': today, 'cycle_type': '2min'}))
    if len(today_stats) == 0:
        print(f"{INFO} {BLUE}Today's Status: No monitoring sessions yet{RESET}")
    else:
        print(f"{CHECK_MARK} {BLUE}Today's Status: {len(today_stats)} monitoring session(s) completed{RESET}")
    
    print(f"{COMPUTER} {BLUE}System: {platform.system()} {platform.release()}{RESET}")
    print(f"{GLOBE} {BLUE}Database: MongoDB Cloud{RESET}")
    print(f"{CYAN}{'='*70}{RESET}")

def print_progress_bar(current, total, width=50):
    """Print progress bar yang modern"""
    progress = int(width * current / total) if total > 0 else 0
    bar = '█' * progress + '░' * (width - progress)
    percentage = (current / total * 100) if total > 0 else 0
    print(f"\r{BLUE}[{bar}] {current}/{total} ({percentage:.1f}%){RESET}", end='', flush=True)

def print_user_status(username, platform, status, followers=None, time_taken=None):
    """Print status user yang modern"""
    platform_icon = PLATFORM_ICONS.get(platform, '📱')
    
    if status == 'START':
        print(f"\n{USER_ICON} {BOLD}{CYAN}Processing: {username}{RESET} {platform_icon} {platform.upper()}")
        print(f"{CLOCK} {BLUE}Started at: {datetime.now(WIB_TZ).strftime('%H:%M:%S')} WIB{RESET}")
    elif status == 'SUCCESS':
        print(f"{CHECK_MARK} {BOLD}{GREEN}SUCCESS{RESET} {username} {platform_icon} {followers:,} followers")
        if time_taken:
            print(f"{CLOCK} {BLUE}Completed in: {time_taken:.2f}s{RESET}")
    elif status == 'ERROR':
        print(f"{CROSS_MARK} {BOLD}{RED}ERROR{RESET} {username} {platform_icon}")
    elif status == 'RETRY':
        print(f"{WARNING} {BOLD}{YELLOW}RETRYING{RESET} {username} {platform_icon}")
    elif status == 'WAITING':
        print(f"{MOON} {BOLD}{BLUE}WAITING{RESET} {username} {platform_icon} - Rate limit protection")

def print_system_stats(chrome_ram, python_ram):
    """Print system stats yang modern"""
    print(f"{COMPUTER} {BLUE}System Resources:{RESET}")
    print(f"  {CYAN}Chrome RAM: {chrome_ram} MB{RESET}")
    print(f"  {CYAN}Python RAM: {python_ram} MB{RESET}")

def print_cycle_summary(success, fail, total, cycle_time):
    """Print ringkasan siklus yang modern"""
    success_rate = (success / total * 100) if total > 0 else 0
    
    print(f"\n{BOLD}{MAGENTA}{'='*70}{RESET}")
    print(f"{ROCKET} {BOLD}{CYAN}CYCLE SUMMARY{RESET}")
    print(f"{CHECK_MARK} {GREEN}Success: {success}{RESET}")
    print(f"{CROSS_MARK} {RED}Failed: {fail}{RESET}")
    print(f"{INFO} {BLUE}Total: {total}{RESET}")
    print(f"{STAR} {BLUE}Success Rate: {success_rate:.1f}%{RESET}")
    print(f"{CLOCK} {BLUE}Cycle Time: {cycle_time:.2f}s{RESET}")
    print(f"{BOLD}{MAGENTA}{'='*70}{RESET}")

def print_countdown():
    """Print countdown yang modern sampai 2 menit berikutnya"""
    target_time = get_next_run_time()
    
    while True:
        now = datetime.now(WIB_TZ)
        time_diff = target_time - now
        
        if time_diff.total_seconds() <= 0:
            print(f"\n{SUN} {GREEN}Time to wake up! Starting daily monitoring...{RESET}")
            break
        
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        seconds = int(time_diff.total_seconds() % 60)
        
        # Clear line dan print countdown dengan format yang lebih baik
        if hours >= 24:
            days = hours // 24
            remaining_hours = hours % 24
            print(f"\r{MOON} {BLUE}Sleeping until next run (7:15 AM WIB daily) - {days}d {remaining_hours:02d}:{minutes:02d}:{seconds:02d}{RESET}", end='', flush=True)
        else:
            print(f"\r{MOON} {BLUE}Sleeping until next run (7:15 AM WIB daily) - {hours:02d}:{minutes:02d}:{seconds:02d}{RESET}", end='', flush=True)
        
        time.sleep(1)

async def print_countdown_async():
    """Print countdown yang modern sampai 2 menit berikutnya (async version)"""
    target_time = get_next_run_time()
    
    while True:
        now = datetime.now(WIB_TZ)
        time_diff = target_time - now
        
        if time_diff.total_seconds() <= 0:
            print(f"\n{SUN} {GREEN}Time to wake up! Starting daily monitoring...{RESET}")
            break
        
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        seconds = int(time_diff.total_seconds() % 60)
        
        # Clear line dan print countdown dengan format yang lebih baik
        if hours >= 24:
            days = hours // 24
            remaining_hours = hours % 24
            print(f"\r{MOON} {BLUE}Sleeping until next run (7:15 AM WIB daily) - {days}d {remaining_hours:02d}:{minutes:02d}:{seconds:02d}{RESET}", end='', flush=True)
        else:
            print(f"\r{MOON} {BLUE}Sleeping until next run (7:15 AM WIB daily) - {hours:02d}:{minutes:02d}:{seconds:02d}{RESET}", end='', flush=True)
        
        await asyncio.sleep(1)

def print_smart_status(username, platform, status, followers=None, time_taken=None, attempt=None):
    """Print status user yang lebih cerdas dengan progress indicator"""
    platform_icon = PLATFORM_ICONS.get(platform, '📱')
    
    if status == 'START':
        print(f"\n{USER_ICON} {BOLD}{CYAN}Processing: {username}{RESET} {platform_icon} {platform.upper()}")
        print(f"{CLOCK} {BLUE}Started at: {datetime.now(WIB_TZ).strftime('%H:%M:%S')} WIB{RESET}")
    elif status == 'SUCCESS':
        print(f"{CHECK_MARK} {BOLD}{GREEN}SUCCESS{RESET} {username} {platform_icon} {followers:,} followers")
        if time_taken:
            print(f"{CLOCK} {BLUE}Completed in: {time_taken:.2f}s{RESET}")
    elif status == 'ERROR':
        print(f"{CROSS_MARK} {BOLD}{RED}ERROR{RESET} {username} {platform_icon}")
    elif status == 'RETRY':
        print(f"{WARNING} {BOLD}{YELLOW}RETRYING (Attempt #{attempt}){RESET} {username} {platform_icon}")
    elif status == 'WAITING':
        print(f"{MOON} {BOLD}{BLUE}WAITING{RESET} {username} {platform_icon} - Rate limit protection")

# --- SETUP DATABASE ---
print("Mencoba terhubung ke database MongoDB cloud 'creator_web'...")
try:
    cloud_client = MongoClient('mongodb+srv://ahmadyazidarifuddin04:Qwerty12345.@creatorweb.zpsu4ci.mongodb.net/?retryWrites=true&w=majority&appName=creatorWeb', serverSelectionTimeoutMS=5000)
    cloud_client.server_info()
    creator_db = cloud_client['creator_web']
    users_collection = creator_db['users']
    stats_collection = creator_db['stats']
    print("Koneksi ke database MongoDB cloud 'creator_web' berhasil.")
except pymongo.errors.ServerSelectionTimeoutError:
    print("Tidak dapat terhubung ke MongoDB cloud.")
    print("Pastikan URI dan koneksi internet benar.")
    exit()
except Exception as e:
    print(f"Error saat membaca database: {e}")
    exit()

async def block_resource(route):
    if route.request.resource_type == "image":
        await route.abort()
    else:
        await route.continue_()

async def stable_sample_followers(get_value_func, page, sample_count=4, interval=0.5, timeout=30):
    """
    Melakukan sampling nilai followers sebanyak sample_count kali (interval detik),
    dan hanya return jika semua hasil sama. Ulangi terus hingga timeout (default 30 detik).
    Jika timeout, return 'N/A'.
    Setelah setiap batch sampling, print sampling dihapus dari terminal.
    """
    start = time.time()
    print(f"[SAMPLING] Mulai sampling followers ({sample_count}x, interval={interval}s, timeout={timeout}s)...")
    while time.time() - start < timeout:
        samples = []
        sample_start = time.time()
        for i in range(sample_count):
            value = await get_value_func(page)
            samples.append(value)
            print(f"[SAMPLING] Sample ke-{i+1}: {value}")
            await asyncio.sleep(interval)
        sample_time = time.time() - sample_start
        # Clear print sampling dari terminal setiap selesai batch
        total_lines = sample_count + 2  # sample lines + 'Selesai...' + 'Mulai...'
        for _ in range(total_lines):
            print("\033[F\033[K", end='')  # Move cursor up and clear line
        # Print ringkasan hasil batch
        if all(s == samples[0] and s not in (None, "N/A", "") for s in samples):
            print(f"[SAMPLING] Semua sample stabil: {samples[0]}")
            return samples[0]
        else:
            c = Counter(samples)
            if c:
                majority, _ = c.most_common(1)[0]
                diff_indices = [(i, v) for i, v in enumerate(samples) if v != majority]
                value_to_indices = defaultdict(list)
                for i, v in diff_indices:
                    value_to_indices[v].append(i)
                print(f"{RED}# Mayoritas: '{majority}'{RESET}")
                if diff_indices:
                    idx_val_strs = []
                    for val, idxs in value_to_indices.items():
                        idxs_str = ','.join(str(i) for i in idxs)
                        idx_val_strs.append(f"{idxs_str} ('{val}')")
                    print(f"{RED}# Index berbeda: {', '.join(idx_val_strs)}{RESET}")
                else:
                    print(f"{RED}# Index berbeda: -{RESET}")
            else:
                print(f"{RED}# Mayoritas: -{RESET}")
                print(f"{RED}# Index berbeda: -{RESET}")
    print(f"[SAMPLING] Timeout, return 'N/A'")
    return "N/A"

# --- PATCH get_instagram_followers dan get_tiktok_followers agar hanya ambil angka saja ---
async def get_instagram_followers_value(page):
    try:
        await page.wait_for_selector("div[aria-label='Follower Count']", timeout=10000)
        value_elements = await page.query_selector_all("div[aria-label='Follower Count'] span.odometer-value, div[aria-label='Follower Count'] span.odometer-formatting-mark")
        texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements]
        follower_text = ''.join(texts)
        follower_count = re.sub(r'[^\d]', '', follower_text)
        return follower_count if follower_count else "N/A"
    except Exception:
        return "N/A"

async def get_tiktok_followers_value(page):
    try:
        await page.wait_for_selector(".odometer-inside", timeout=10000)
        odometers = await page.query_selector_all(".odometer-inside")
        if odometers:
            value_spans = await odometers[0].query_selector_all(".odometer-value")
            texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_spans]
            follower_count = ''.join(texts)
            return follower_count if follower_count else "N/A"
        return "N/A"
    except Exception:
        return "N/A"

async def wait_for_instagram_animation(page, timeout=10):
    start = time.time()
    valid_value = None
    while time.time() - start < timeout:
        try:
            value_elements = await page.query_selector_all("div[aria-label='Follower Count'] span.odometer-value, div[aria-label='Follower Count'] span.odometer-formatting-mark")
            texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements]
            value = ''.join(texts)
            value_digits = re.sub(r'\D', '', value)
            if value_digits and value_digits.isdigit() and len(value_digits) > 3:
                stable = True
                for _ in range(10):
                    await asyncio.sleep(0.05)
                    value_elements2 = await page.query_selector_all("div[aria-label='Follower Count'] span.odometer-value, div[aria-label='Follower Count'] span.odometer-formatting-mark")
                    texts2 = [await page.evaluate('(el) => el.textContent', elem) for elem in value_elements2]
                    value2 = ''.join(texts2)
                    value_digits2 = re.sub(r'\D', '', value2)
                    if value_digits2 != value_digits:
                        stable = False
                        break
                if stable:
                    valid_value = value_digits
                    break
        except Exception:
            pass
    if not valid_value:
        print("[wait_for_instagram_animation] Gagal mendapatkan angka followers yang valid dan stabil dalam 10 detik.")

async def get_tiktok_followers(page):
    try:
        await page.wait_for_selector(".odometer-inside", timeout=10000)
        odometers = await page.query_selector_all(".odometer-inside")
        if odometers:
            value_spans = await odometers[0].query_selector_all(".odometer-value")
            texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_spans]
            return ''.join(texts)
        return "N/A"
    except Exception:
        return "N/A"

async def wait_for_tiktok_animation(page, timeout=6):
    last_value = None
    stable_count = 0
    start = time.time()
    while time.time() - start < timeout:
        try:
            odometers = await page.query_selector_all(".odometer-inside")
            if odometers:
                value_spans = await odometers[0].query_selector_all(".odometer-value")
                texts = [await page.evaluate('(el) => el.textContent', elem) for elem in value_spans]
                value = ''.join(texts)
                if value == last_value and value != "":
                    stable_count += 1
                    if stable_count >= 10:
                        break
                else:
                    stable_count = 1
                last_value = value
        except Exception:
            pass
        await asyncio.sleep(0.05)

async def handle_tiktok_cookie_popup(page):
    try:
        await page.wait_for_selector("div > div > div:nth-child(1) > button", timeout=5000)
        await page.click("div > div > div:nth-child(1) > button")
        await asyncio.sleep(1)
    except Exception:
        pass

async def main_loop():
    base_urls = {
        'instagram': "https://livecounts.nl/instagram-realtime/?u={username}",
        'tiktok': "https://tokcounter.com/id?user={username}"
    }
    
    print(f"{SUN} {BOLD}{GREEN}Bot started successfully!{RESET}")
    print(f"{INFO} {BLUE}Bot will run automatically every 2 minutes{RESET}")
    
    async with async_playwright() as p:
        try:
            while True:
                # Cek apakah sudah waktunya untuk monitoring (setiap 2 menit)
                now = datetime.now(WIB_TZ)
                next_run = get_next_run_time()
                
                # Jika belum waktunya, tunggu dulu
                if now < next_run:
                    clear_screen()
                    print_header()
                    print(f"\n{MOON} {BOLD}{BLUE}Waiting until next 2-minute cycle...{RESET}")
                    print(f"{INFO} {BLUE}Current time: {now.strftime('%H:%M:%S')} WIB{RESET}")
                    print(f"{SUN} {BLUE}Next monitoring at: {next_run.strftime('%H:%M:%S')} WIB{RESET}")
                    
                    # Tunggu sampai 2 menit berikutnya
                    await print_countdown_async()
                
                # Mulai monitoring cycle
                clear_screen()
                print_header()
                now = datetime.now(WIB_TZ)
                print(f"\n{ROCKET} {BOLD}{CYAN}Starting 2-minute monitoring cycle...{RESET}")
                print(f"{CLOCK} {BLUE}2-minute cycle started at: {now.strftime('%H:%M:%S')} WIB{RESET}")
                print(f"{INFO} {BLUE}Monitoring Date: {now.strftime('%A, %d %B %Y')}{RESET}")
                
                # Cek apakah ini monitoring pertama hari ini
                today = datetime.now(WIB_TZ).strftime('%Y-%m-%d')
                today_stats = list(stats_collection.find({'date': today, 'cycle_type': '2min'}))
                if len(today_stats) == 0:
                    print(f"{STAR} {BLUE}First monitoring session of the day{RESET}")
                else:
                    print(f"{INFO} {BLUE}Monitoring session #{len(today_stats) + 1} of the day{RESET}")
                
                siklus_start = time.time()
                users_to_monitor = []
                users_from_db = list(users_collection.find({}, {'socialLinks': 1, '_id': 1}))
                for user in users_from_db:
                    social = user.get('socialLinks', {})
                    if 'instagram' in social and social['instagram']:
                        users_to_monitor.append({'_id': user['_id'], 'username': social['instagram'], 'platform': 'instagram'})
                    if 'tiktok' in social and social['tiktok']:
                        users_to_monitor.append({'_id': user['_id'], 'username': social['tiktok'], 'platform': 'tiktok'})
                
                total_success = 0
                total_fail = 0
                stats_data = []
                
                browser = await p.chromium.launch(headless=True, args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--window-size=100,100',
                    '--mute-audio',
                    '--disable-infobars',
                    '--disable-notifications',
                ])
                context = await browser.new_context(user_agent='Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36')
                
                try:
                    print(f"\n{INFO} {BLUE}Found {len(users_to_monitor)} users to monitor{RESET}")
                    print(f"{CYAN}{'─'*70}{RESET}")
                    
                    for i, user_info in enumerate(users_to_monitor, 1):
                        print_smart_status(user_info['username'], user_info['platform'], 'START')
                        user_start = time.time()
                        url = base_urls[user_info['platform']].format(username=user_info['username'])
                        attempt = 0
                        max_delay = 300  # maksimal delay 5 menit
                        success = False
                        
                        # Rate limiting: tunggu 2-5 detik antara user
                        if i > 1:
                            wait_time = 2 + (i % 3)  # 2, 3, atau 4 detik
                            print_smart_status(user_info['username'], user_info['platform'], 'WAITING')
                            await asyncio.sleep(wait_time)
                        
                        while not success:
                            try:
                                print(f"{GLOBE} {BLUE}Opening browser tab...{RESET}")
                                print(f"{INFO} {CYAN}URL: {url}{RESET}")
                                page = await context.new_page()
                                await page.route("**/*", block_resource)
                                
                                # Cerdas: Coba dengan timeout yang berbeda berdasarkan attempt
                                timeout_values = [30000, 45000, 60000, 90000]  # 30s, 45s, 60s, 90s
                                timeout = timeout_values[min(attempt, len(timeout_values) - 1)]
                                
                                print(f"{CLOCK} {BLUE}Timeout: {timeout}ms{RESET}")
                                await page.goto(url, timeout=timeout, wait_until='domcontentloaded')
                                
                                # Cerdas: Tunggu sampai halaman benar-benar load
                                try:
                                    await page.wait_for_load_state('networkidle', timeout=10000)
                                except Exception:
                                    print(f"{WARNING} {YELLOW}Network idle timeout, continuing...{RESET}")
                                
                                # Cerdas: Cek apakah URL berhasil dibuka
                                for _ in range(50):  # Tunggu lebih lama
                                    if page.url == url or user_info['platform'] in page.url:
                                        break
                                    await asyncio.sleep(0.2)
                                
                                print(f"{CHECK_MARK} {GREEN}Browser tab opened successfully{RESET}")
                                if user_info['platform'] == 'tiktok':
                                    await asyncio.sleep(2)
                                    await handle_tiktok_cookie_popup(page)
                                
                                while True:
                                    sample_time_start = time.time()
                                    if user_info['platform'] == 'instagram':
                                        follower_count_str = await stable_sample_followers(get_instagram_followers_value, page)
                                        follower_count_int = clean_and_convert_to_int(follower_count_str)
                                        sample_time = time.time() - sample_time_start
                                        print(f"[RESULT] Instagram followers: {follower_count_str} (int: {follower_count_int}), waktu sampling: {sample_time:.2f} detik")
                                        if follower_count_int is not None and follower_count_int > 0:
                                            users_collection.update_one(
                                                { '_id': user_info['_id'] },
                                                { '$set': { 'instagramFollowers': follower_count_int } }
                                            )
                                            stats_data.append({
                                                'username': user_info['username'],
                                                'platform': 'instagram',
                                                'followers': follower_count_int
                                            })
                                            user_time = time.time() - user_start
                                            print_smart_status(user_info['username'], user_info['platform'], 'SUCCESS', follower_count_int, user_time)
                                            chrome_ram = get_chrome_memory_usage()
                                            python_ram = get_python_memory_usage()
                                            print_system_stats(chrome_ram, python_ram)
                                            total_success += 1
                                            success = True
                                            break
                                        else:
                                            print(f"{WARNING} {YELLOW}Invalid followers data: '{follower_count_str}'{RESET}")
                                            print_smart_status(user_info['username'], user_info['platform'], 'RETRY', attempt=attempt+1)
                                    elif user_info['platform'] == 'tiktok':
                                        followers = await stable_sample_followers(get_tiktok_followers_value, page)
                                        followers_int = clean_and_convert_to_int(followers)
                                        sample_time = time.time() - sample_time_start
                                        print(f"[RESULT] TikTok followers: {followers} (int: {followers_int}), waktu sampling: {sample_time:.2f} detik")
                                        if followers != "N/A" and followers_int is not None and followers_int > 0:
                                            users_collection.update_one(
                                                { '_id': user_info['_id'] },
                                                { '$set': { 'tiktokFollowers': followers_int } }
                                            )
                                            stats_data.append({
                                                'username': user_info['username'],
                                                'platform': 'tiktok',
                                                'followers': followers_int
                                            })
                                            user_time = time.time() - user_start
                                            print_smart_status(user_info['username'], user_info['platform'], 'SUCCESS', followers_int, user_time)
                                            chrome_ram = get_chrome_memory_usage()
                                            python_ram = get_python_memory_usage()
                                            print_system_stats(chrome_ram, python_ram)
                                            total_success += 1
                                            success = True
                                            break
                                        else:
                                            print(f"{WARNING} {YELLOW}Invalid followers data: '{followers}'{RESET}")
                                            print_smart_status(user_info['username'], user_info['platform'], 'RETRY', attempt=attempt+1)
                                await page.close()
                                break
                            except Exception as e:
                                # Cerdas: Pastikan page ditutup jika terjadi error
                                try:
                                    await page.close()
                                except Exception:
                                    pass
                                
                                attempt += 1
                                delay = min(2 ** attempt, max_delay)
                                
                                # Cerdas: Handle TimeoutError secara khusus
                                if 'TimeoutError' in str(type(e)):
                                    print(f"{WARNING} {YELLOW}Website timeout, attempt #{attempt}{RESET}")
                                    if attempt % 3 == 0:
                                        print(f"{INFO} {BLUE}Restarting browser context...{RESET}")
                                        try:
                                            await context.close()
                                        except Exception:
                                            pass
                                        context = await browser.new_context(user_agent='Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36')
                                else:
                                    print(f"{CROSS_MARK} {RED}Exception: {type(e).__name__}: {e}{RESET}")
                                    traceback.print_exc()
                                
                                print(f"{CLOCK} {BLUE}Retrying in {delay}s...{RESET}")
                                
                                # Cerdas: Restart context setiap 5x gagal untuk semua error
                                if attempt % 5 == 0:
                                    print(f"{INFO} {BLUE}Restarting browser context for recovery...{RESET}")
                                    try:
                                        await context.close()
                                    except Exception:
                                        pass
                                    context = await browser.new_context(user_agent='Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36')
                                
                                await asyncio.sleep(delay)
                        print(f"{CYAN}{'─'*70}{RESET}")
                except Exception as e:
                    print(f"{RED}[EXCEPTION] {type(e).__name__}: {e}{RESET}")
                    traceback.print_exc()
                    if 'TimeoutError' in str(type(e)) or 'NetworkError' in str(type(e)):
                        print(f"{RED}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {'N/A'.rjust(15)}  RETRY{RESET}")
                        await asyncio.sleep(2)
                        continue
                    print(f"{RED}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {'N/A'.rjust(15)}  FATAL ERROR: {type(e).__name__}{RESET}")
                    total_fail += 1
                    break
                finally:
                    await context.clear_cookies()
                    await context.close()
                
                # --- Tutup browser setelah siklus selesai ---
                print(f"{CYAN}{'─'*70}{RESET}")
                chrome_ram = get_chrome_memory_usage()
                python_ram = get_python_memory_usage()
                print(f"{YELLOW}[INFO] RAM Chrome sebelum browser Playwright ditutup: {chrome_ram} MB, RAM Python: {python_ram} MB, File kode = {get_code_file_size()} KB{RESET}")
                print(f"{YELLOW}[INFO] Menutup browser Playwright...{RESET}")
                await browser.close()
                print(f"{YELLOW}[INFO] Browser Playwright sudah ditutup.{RESET}")
                gc.collect()
                chrome_ram_after = get_chrome_memory_usage()
                python_ram_after = get_python_memory_usage()
                print(f"{YELLOW}[INFO] RAM Chrome setelah browser Playwright ditutup: {chrome_ram_after} MB, RAM Python: {python_ram_after} MB, File kode = {get_code_file_size()} KB{RESET}")
                print(f"{CYAN}{'─'*70}{RESET}")
                
                siklus_time = time.time() - siklus_start
                print_cycle_summary(total_success, total_fail, len(users_to_monitor), siklus_time)
                
                # Hitung berapa kali monitoring sudah dilakukan hari ini
                today = datetime.now(WIB_TZ).strftime('%Y-%m-%d')
                today_stats = list(stats_collection.find({'date': today, 'cycle_type': 'daily'}))
                monitoring_count = len(today_stats) + 1
                
                stats_collection.insert_one({
                    'timestamp': datetime.now(timezone.utc),
                    'date': datetime.now(WIB_TZ).strftime('%Y-%m-%d'),
                    'cycle_type': '2min',
                    'monitoring_count': monitoring_count,
                    'data': stats_data
                })
                print(f"{CHECK_MARK} {GREEN}Statistics sent to MongoDB (2-minute monitoring #{monitoring_count}){RESET}")
                print(f"{INFO} {BLUE}Total 2-minute monitoring sessions today: {monitoring_count}{RESET}")
                print(f"{CYAN}{'─'*70}{RESET}")
                print(f"{COMPUTER} {BLUE}Active Chrome processes:{RESET}")
                for proc in get_chrome_processes():
                    print(f"  {CYAN}PID={proc.info['pid']} NAME={proc.info['name']} RAM={round(proc.info['memory_info'].rss/1024/1024,2)} MB{RESET}")
                
                # Tampilkan ringkasan waktu sampai monitoring berikutnya
                next_run = get_next_run_time()
                time_until_next = next_run - datetime.now(WIB_TZ)
                hours_until_next = int(time_until_next.total_seconds() // 3600)
                minutes_until_next = int((time_until_next.total_seconds() % 3600) // 60)
                
                if hours_until_next >= 24:
                    days_until_next = hours_until_next // 24
                    remaining_hours = hours_until_next % 24
                    print(f"{CLOCK} {BLUE}Next 2-minute monitoring in: {days_until_next} days, {remaining_hours} hours, {minutes_until_next} minutes{RESET}")
                else:
                    print(f"{CLOCK} {BLUE}Next 2-minute monitoring in: {hours_until_next} hours, {minutes_until_next} minutes{RESET}")
                
                print(f"\n{SUN} {GREEN}2-minute monitoring cycle completed successfully!{RESET}")
                print(f"{CHECK_MARK} {GREEN}Today's monitoring session #{monitoring_count} finished{RESET}")
                print(f"{INFO} {BLUE}Total monitoring sessions today: {monitoring_count}{RESET}")
                print(f"{MOON} {BLUE}Bot will sleep until next run (every 2 minutes){RESET}")
                
                # Tampilkan informasi next run
                next_run = get_next_run_time()
                now = datetime.now(WIB_TZ)
                time_diff = next_run - now
                days_until_next = time_diff.days
                
                # Tampilkan ringkasan waktu sampai monitoring berikutnya
                total_hours = int(time_diff.total_seconds() // 3600)
                total_minutes = int((time_diff.total_seconds() % 3600) // 60)
                if total_hours >= 24:
                    remaining_days = total_hours // 24
                    remaining_hours = total_hours % 24
                    print(f"{CLOCK} {BLUE}Sleep duration: {remaining_days} days, {remaining_hours} hours, {total_minutes} minutes{RESET}")
                else:
                    print(f"{CLOCK} {BLUE}Sleep duration: {total_hours} hours, {total_minutes} minutes{RESET}")
                
                if days_until_next == 0:
                    print(f"{INFO} {BLUE}Next monitoring: In 2 minutes{RESET}")
                elif days_until_next == 1:
                    print(f"{INFO} {BLUE}Next monitoring: Tomorrow{RESET}")
                else:
                    print(f"{INFO} {BLUE}Next monitoring: In {days_until_next} days{RESET}")
                
                # Tampilkan status monitoring hari ini
                if monitoring_count == 1:
                    print(f"{STAR} {BLUE}Status: First monitoring session of the day completed{RESET}")
                else:
                    print(f"{INFO} {BLUE}Status: Monitoring session #{monitoring_count} of the day completed{RESET}")
                
                print(f"{CYAN}{'─'*70}{RESET}")
                print(f"{INFO} {BLUE}2-minute monitoring cycle completed. Waiting for next cycle...{RESET}")
                
        except KeyboardInterrupt:
            print(f"\n{WARNING} {YELLOW}Bot stopped by user.{RESET}")
        finally:
            print(f"\n{INFO} {BLUE}Closing browser...{RESET}")
            try:
                await browser.close()
            except Exception:
                pass
            print(f"{CHECK_MARK} {GREEN}Bot finished.{RESET}")

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nBot dihentikan oleh pengguna.")
    except Exception as e:
        print(f"\nTerjadi kesalahan fatal: {e}")
    finally:
        print("\nMenutup browser...")
        print("Bot selesai.")
    