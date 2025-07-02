import asyncio
from playwright.async_api import async_playwright
import time
from datetime import datetime, timezone
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

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'
YELLOW = '\033[93m'

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

async def stable_sample_followers(get_value_func, page, sample_count=20, interval=0.1, timeout=30):
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
    async with async_playwright() as p:
        try:
            while True:
                clear_screen()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Mulai siklus monitoring...")
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
                    for user_info in users_to_monitor:
                        print("-" * 50)
                        print(f"\n[USER] Mulai proses untuk {user_info['username']} ({user_info['platform']}) pada {datetime.now().strftime('%H:%M:%S')}")
                        user_start = time.time()
                        url = base_urls[user_info['platform']].format(username=user_info['username'])
                        retry_count = 0
                        while retry_count < 3:
                            try:
                                print(f"[BROWSER] Membuka tab untuk {user_info['username']} ({user_info['platform']})... URL: {url}")
                                page = await context.new_page()
                                await page.route("**/*", block_resource)
                                await page.goto(url, timeout=30000)
                                for _ in range(30):
                                    if page.url == url:
                                        break
                                    await asyncio.sleep(0.1)
                                print(f"[BROWSER] Tab untuk '{user_info['username']}' ({user_info['platform']}) dibuka.")
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
                                            print(f"{GREEN}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {str(follower_count_int).rjust(15)}  OK{RESET}")
                                            chrome_ram = get_chrome_memory_usage()
                                            python_ram = get_python_memory_usage()
                                            print(f"[RAM] Chrome: {chrome_ram} MB | Python: {python_ram} MB")
                                            total_success += 1
                                            break
                                        else:
                                            print(f"{YELLOW}[ERROR] Tidak dapat mengambil followers valid untuk {user_info['username']} (instagram): '{follower_count_str}'{RESET}")
                                            print(f"{RED}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {'N/A'.rjust(15)}  RETRY{RESET}")
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
                                            print(f"{GREEN}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {followers.rjust(15)}  OK{RESET}")
                                            chrome_ram = get_chrome_memory_usage()
                                            python_ram = get_python_memory_usage()
                                            print(f"[RAM] Chrome: {chrome_ram} MB | Python: {python_ram} MB")
                                            total_success += 1
                                            break
                                        else:
                                            print(f"{YELLOW}[ERROR] Tidak dapat mengambil followers valid untuk {user_info['username']} (tiktok): '{followers}'{RESET}")
                                            print(f"{RED}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {'N/A'.rjust(15)}  RETRY{RESET}")
                                await page.close()
                                break
                            except Exception as e:
                                print(f"{RED}[EXCEPTION] {type(e).__name__}: {e}{RESET}")
                                traceback.print_exc()
                                if 'TimeoutError' in str(type(e)) or 'NetworkError' in str(type(e)):
                                    retry_count += 1
                                    if retry_count < 3:
                                        print(f"{RED}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {'N/A'.rjust(15)}  RETRY{RESET}")
                                        await asyncio.sleep(2)
                                        continue
                                print(f"{RED}{user_info['username'].ljust(20)} {user_info['platform'].ljust(12)} {'N/A'.rjust(15)}  FATAL ERROR: {type(e).__name__}{RESET}")
                                total_fail += 1
                                break
                        user_time = time.time() - user_start
                        print(f"[USER] Selesai proses untuk {user_info['username']} ({user_info['platform']}) dalam {user_time:.2f} detik pada {datetime.now().strftime('%H:%M:%S')}")
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
                print("-" * 60)
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
                print("-" * 60)
                siklus_time = time.time() - siklus_start
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sukses: {total_success} | Gagal: {total_fail} | Total: {len(users_to_monitor)} user | Lama siklus: {siklus_time:.2f} detik")
                stats_collection.insert_one({
                    'timestamp': datetime.now(timezone.utc),
                    'data': stats_data
                })
                print(f"{YELLOW}[INFO] Data statistik berhasil dikirim ke MongoDB pada [{datetime.now().strftime('%H:%M:%S')}] {RESET}")
                print("-" * 60)
                print("[DEBUG] Proses Chrome/Chromium aktif:")
                for proc in get_chrome_processes():
                    print(f"  PID={proc.info['pid']} NAME={proc.info['name']} RAM={round(proc.info['memory_info'].rss/1024/1024,2)} MB")
                print("Menunggu 2 menit sebelum siklus berikutnya:")
                for i in range(1, 121):
                    print(f"\rStopwatch: {i}", end='', flush=True)
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nBot dihentikan oleh pengguna.")
        finally:
            print("\nMenutup browser...")
            try:
                await browser.close()
            except Exception:
                pass
            print("Bot selesai.")

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
    