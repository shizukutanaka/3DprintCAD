import requests
import sys
from pathlib import Path

def check_url(url):
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

# プロジェクト内のURLをチェック
urls = [
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
    'https://cdn.jsdelivr.net/npm/axios@1.6.7/dist/axios.min.js',
    'https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.min.js',
    'https://cdn.jsdelivr.net/npm/three@0.160.1/examples/jsm/controls/OrbitControls.js',
    'https://cdn.jsdelivr.net/npm/three@0.160.1/examples/jsm/loaders/STLLoader.js',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
    'https://cdn.jsdelivr.net/npm/tailwindcss@3.4.1/dist/tailwind.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    # 存在しないURLの例として追加
    'https://example.com/nonexistent.css',
    'https://invalid-domain-12345.com/file.js'
]

valid_urls = []
invalid_urls = []

for url in urls:
    if check_url(url):
        valid_urls.append(url)
    else:
        invalid_urls.append(url)

print("有効なURL:")
for url in valid_urls:
    print(f"  {url}")

print("\n無効なURL:")
for url in invalid_urls:
    print(f"  {url}")

print(f"\n合計: {len(valid_urls)} 有効, {len(invalid_urls)} 無効")
