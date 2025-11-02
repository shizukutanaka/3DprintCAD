#!/usr/bin/env python3
"""
プログレッシブ・ウェブアプリシステム
モバイルとタブレットに最適化されたユーザーインターフェース
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

@dataclass
class PWAConfig:
    """PWA設定"""
    name: str = "3D Print CAD Assistant"
    short_name: str = "3D CAD"
    description: str = "Advanced 3D printing CAD tool with AI assistance"
    start_url: str = "/"
    display: str = "standalone"
    background_color: str = "#ffffff"
    theme_color: str = "#007bff"
    orientation: str = "any"
    scope: str = "/"
    lang: str = "en"

    # アイコン設定
    icons: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.icons is None:
            self.icons = [
                {
                    "src": "/static/icons/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "maskable any"
                },
                {
                    "src": "/static/icons/icon-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable any"
                }
            ]

class ProgressiveWebAppManager:
    """プログレッシブ・ウェブアプリ管理システム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.pwa_config = PWAConfig()
        self._offline_cache = set()

    def generate_manifest(self) -> str:
        """ウェブアプリマニフェストを生成"""
        manifest_data = {
            "name": self.pwa_config.name,
            "short_name": self.pwa_config.short_name,
            "description": self.pwa_config.description,
            "start_url": self.pwa_config.start_url,
            "display": self.pwa_config.display,
            "background_color": self.pwa_config.background_color,
            "theme_color": self.pwa_config.theme_color,
            "orientation": self.pwa_config.orientation,
            "scope": self.pwa_config.scope,
            "lang": self.pwa_config.lang,
            "icons": self.pwa_config.icons,
            "categories": ["productivity", "utilities", "developer"],
            "screenshots": [
                {
                    "src": "/static/screenshots/desktop.png",
                    "sizes": "1280x720",
                    "type": "image/png",
                    "form_factor": "wide"
                },
                {
                    "src": "/static/screenshots/mobile.png",
                    "sizes": "390x844",
                    "type": "image/png",
                    "form_factor": "narrow"
                }
            ]
        }

        return json.dumps(manifest_data, ensure_ascii=False, indent=2)

    def generate_service_worker(self) -> str:
        """サービスワーカーを生成"""
        sw_code = """// Progressive Web App Service Worker
const CACHE_NAME = '3d-cad-assistant-v1';
const OFFLINE_URL = '/offline.html';

// キャッシュ対象のリソース
const CACHE_RESOURCES = [
    '/',
    '/static/css/main.css',
    '/static/js/main.js',
    '/static/js/three.min.js',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png',
    '/offline.html'
];

// インストールイベント
self.addEventListener('install', (event) => {
    console.log('Service Worker installing.');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Caching app shell');
                return cache.addAll(CACHE_RESOURCES);
            })
    );
});

// アクティベートイベント
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating.');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// フェッチイベント（オフライン対応）
self.addEventListener('fetch', (event) => {
    // APIリクエストはネットワーク優先
    if (event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    // オフライン時はエラーを返す
                    return new Response(
                        JSON.stringify({ error: 'Offline - API unavailable' }),
                        {
                            status: 503,
                            headers: { 'Content-Type': 'application/json' }
                        }
                    );
                })
        );
        return;
    }

    // その他のリクエストはキャッシュ優先でフォールバック
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // キャッシュがある場合はそれを返す
                if (response) {
                    return response;
                }

                // キャッシュがない場合はネットワークから取得
                return fetch(event.request)
                    .then((response) => {
                        // 有効なレスポンスの場合のみキャッシュ
                        if (response && response.status === 200) {
                            const responseClone = response.clone();
                            caches.open(CACHE_NAME)
                                .then((cache) => {
                                    cache.put(event.request, responseClone);
                                });
                        }
                        return response;
                    })
                    .catch(() => {
                        // オフライン時はオフラインページを返す
                        if (event.request.destination === 'document') {
                            return caches.match(OFFLINE_URL);
                        }
                        // 画像などの場合はデフォルトアイコンを返す
                        return new Response('', { status: 408 });
                    });
            })
    );
});

// プッシュ通知（オプション）
self.addEventListener('push', (event) => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-192x192.png',
            vibrate: [100, 50, 100],
            data: data.url,
            actions: [
                {
                    action: 'open',
                    title: 'Open App',
                    icon: '/static/icons/icon-192x192.png'
                },
                {
                    action: 'close',
                    title: 'Close'
                }
            ]
        };

        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// 通知クリックイベント
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'open') {
        event.waitUntil(
            clients.openWindow(event.notification.data || '/')
        );
    }
});

// バックグラウンド同期（オプション）
self.addEventListener('sync', (event) => {
    if (event.tag === 'background-sync') {
        event.waitUntil(
            // バックグラウンド処理
            doBackgroundSync()
        );
    }
});

async function doBackgroundSync() {
    // オフライン時のデータを同期
    console.log('Background sync triggered');
}

// メッセージイベント（メインアプリからの通信）
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
"""

        return sw_code

    def generate_offline_page(self) -> str:
        """オフラインページを生成"""
        offline_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Print CAD Assistant - Offline</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .offline-container {
            max-width: 400px;
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        .icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        .title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .message {
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 30px;
            opacity: 0.9;
        }
        .retry-btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .retry-btn:hover {
            background: #0056b3;
        }
        .features {
            margin-top: 30px;
            text-align: left;
        }
        .feature {
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }
        .feature-icon {
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="offline-container">
        <div class="icon">📱</div>
        <h1 class="title">You're Offline</h1>
        <p class="message">
            Don't worry! Your 3D Print CAD Assistant works offline too.
            You can still view your designs and make basic edits.
        </p>
        <button class="retry-btn" onclick="window.location.reload()">
            Try Again
        </button>

        <div class="features">
            <h3>Offline Features Available:</h3>
            <div class="feature">
                <span class="feature-icon">✓</span>
                View saved designs
            </div>
            <div class="feature">
                <span class="feature-icon">✓</span>
                Basic mesh editing
            </div>
            <div class="feature">
                <span class="feature-icon">✓</span>
                Export to STL format
            </div>
            <div class="feature">
                <span class="feature-icon">✓</span>
                Visual programming blocks
            </div>
        </div>
    </div>

    <script>
        // オフライン状態をチェック
        window.addEventListener('online', () => {
            window.location.reload();
        });

        // インストールプロンプト（PWAの場合）
        if ('serviceWorker' in navigator) {
            window.addEventListener('beforeinstallprompt', (e) => {
                // インストールバナーを表示するロジック
                console.log('PWA installation available');
            });
        }
    </script>
</body>
</html>"""

        return offline_html

    def generate_mobile_optimized_css(self) -> str:
        """モバイル最適化CSSを生成"""
        css = """
/* Progressive Web App Mobile Optimizations */

/* レスポンシブデザインの基本 */
* {
    box-sizing: border-box;
}

html {
    font-size: 16px;
    -webkit-text-size-adjust: 100%;
    -webkit-tap-highlight-color: transparent;
}

body {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f8f9fa;
}

/* モバイルファーストのアプローチ */
.container {
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 15px;
}

/* ナビゲーションバー（モバイル対応） */
.navbar {
    background: #fff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    position: sticky;
    top: 0;
    z-index: 1000;
}

.navbar-brand {
    font-size: 1.25rem;
    font-weight: 600;
    color: #007bff !important;
}

.navbar-toggler {
    border: none;
    background: transparent;
    font-size: 1.25rem;
    color: #007bff;
    cursor: pointer;
}

/* グリッドシステム */
.row {
    display: flex;
    flex-wrap: wrap;
    margin: 0 -15px;
}

.col {
    flex: 1;
    padding: 0 15px;
    min-width: 0;
}

.col-12 { flex: 0 0 100%; max-width: 100%; }
.col-6 { flex: 0 0 50%; max-width: 50%; }
.col-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
.col-8 { flex: 0 0 66.666667%; max-width: 66.666667%; }

/* タッチフレンドリーなボタン */
.btn {
    display: inline-block;
    padding: 12px 24px;
    font-size: 16px;
    font-weight: 500;
    text-align: center;
    text-decoration: none;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    min-height: 48px; /* タッチターゲットサイズ */
    min-width: 48px;
    user-select: none;
    -webkit-user-select: none;
}

.btn-primary {
    background-color: #007bff;
    color: white;
}

.btn-primary:hover, .btn-primary:focus {
    background-color: #0056b3;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,123,255,0.3);
}

.btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* フォーム要素 */
.form-group {
    margin-bottom: 20px;
}

.form-label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #495057;
}

.form-input {
    width: 100%;
    padding: 12px 16px;
    font-size: 16px;
    border: 2px solid #e9ecef;
    border-radius: 8px;
    transition: border-color 0.3s ease;
    min-height: 48px;
}

.form-input:focus {
    outline: none;
    border-color: #007bff;
    box-shadow: 0 0 0 3px rgba(0,123,255,0.25);
}

/* カードレイアウト */
.card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    overflow: hidden;
    margin-bottom: 20px;
}

.card-header {
    padding: 20px;
    background: #f8f9fa;
    border-bottom: 1px solid #e9ecef;
}

.card-body {
    padding: 20px;
}

.card-footer {
    padding: 20px;
    background: #f8f9fa;
    border-top: 1px solid #e9ecef;
}

/* 3Dビューワー（モバイル対応） */
.viewer-container {
    position: relative;
    width: 100%;
    height: 300px; /* モバイルでは小さめに */
    border-radius: 8px;
    overflow: hidden;
    background: #f8f9fa;
}

.viewer-controls {
    position: absolute;
    bottom: 10px;
    left: 10px;
    right: 10px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.viewer-btn {
    flex: 1;
    min-width: 60px;
    height: 36px;
    background: rgba(255,255,255,0.9);
    border: none;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.3s ease;
}

.viewer-btn:hover {
    background: rgba(255,255,255,1);
}

/* ビジュアルプログラミングブロック（モバイル対応） */
.block-palette {
    display: flex;
    overflow-x: auto;
    gap: 8px;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 8px;
    margin-bottom: 15px;
}

.block-item {
    min-width: 80px;
    height: 60px;
    background: #007bff;
    color: white;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    cursor: pointer;
    transition: transform 0.2s ease;
    flex-shrink: 0;
}

.block-item:hover {
    transform: translateY(-2px);
}

.canvas-area {
    min-height: 400px;
    background: white;
    border: 2px dashed #dee2e6;
    border-radius: 8px;
    position: relative;
    overflow: auto;
    touch-action: none; /* タッチ操作を有効化 */
}

/* レスポンシブユーティリティ */
@media (min-width: 576px) {
    .viewer-container {
        height: 400px;
    }

    .block-item {
        min-width: 100px;
        height: 70px;
        font-size: 12px;
    }
}

@media (min-width: 768px) {
    .container {
        padding: 0 30px;
    }

    .viewer-container {
        height: 500px;
    }

    .col-md-6 { flex: 0 0 50%; max-width: 50%; }
    .col-md-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
    .col-md-8 { flex: 0 0 66.666667%; max-width: 66.666667%; }
}

/* ダークモード対応（オプション） */
@media (prefers-color-scheme: dark) {
    body {
        background-color: #1a1a1a;
        color: #ffffff;
    }

    .card {
        background: #2d2d2d;
        color: #ffffff;
    }

    .form-input {
        background: #2d2d2d;
        border-color: #495057;
        color: #ffffff;
    }
}

/* タッチデバイス向けの最適化 */
@media (hover: none) and (pointer: coarse) {
    .btn, .block-item, .viewer-btn {
        min-height: 48px;
        min-width: 48px;
    }

    /* タッチデバイスではホバー効果を無効化 */
    .btn:hover, .block-item:hover, .viewer-btn:hover {
        transform: none;
    }
}

/* インストールプロンプトのスタイル */
.install-prompt {
    position: fixed;
    bottom: 20px;
    left: 20px;
    right: 20px;
    background: #007bff;
    color: white;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 1000;
}

.install-prompt.hidden {
    display: none;
}

.install-prompt button {
    background: white;
    color: #007bff;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 500;
    margin-left: 10px;
    cursor: pointer;
}

/* プルダウンリフレッシュ（モバイル） */
.pull-to-refresh {
    text-align: center;
    padding: 10px;
    color: #6c757d;
    font-size: 14px;
}

/* ローディングアニメーション */
.loading-spinner {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #007bff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* タブナビゲーション（モバイル対応） */
.tab-navigation {
    display: flex;
    background: white;
    border-bottom: 1px solid #dee2e6;
    overflow-x: auto;
}

.tab-item {
    flex: 1;
    padding: 15px 10px;
    text-align: center;
    border: none;
    background: transparent;
    cursor: pointer;
    transition: background-color 0.3s ease;
    white-space: nowrap;
    min-width: 80px;
}

.tab-item.active {
    background-color: #007bff;
    color: white;
}

.tab-content {
    display: none;
    padding: 20px;
}

.tab-content.active {
    display: block;
}

/* モーダルダイアログ（モバイル対応） */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    display: none;
    z-index: 2000;
    overflow-y: auto;
}

.modal.show {
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-dialog {
    background: white;
    border-radius: 12px;
    max-width: 90vw;
    max-height: 90vh;
    overflow: auto;
    margin: 20px;
}

.modal-header {
    padding: 20px;
    border-bottom: 1px solid #dee2e6;
}

.modal-body {
    padding: 20px;
}

.modal-footer {
    padding: 20px;
    border-top: 1px solid #dee2e6;
}

/* スワイプジェスチャー対応 */
.swipeable {
    touch-action: pan-y;
}

/* パフォーマンス最適化 */
.viewer-container canvas {
    max-width: 100%;
    height: auto;
}

/* アクセシビリティ向上 */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* 印刷スタイル */
@media print {
    .navbar, .btn, .modal {
        display: none !important;
    }

    body {
        background: white !important;
        color: black !important;
    }
}
"""

        return css

    def create_pwa_files(self, static_dir: Path):
        """PWAファイルを生成"""
        # マニフェストファイル
        manifest_path = static_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_manifest())

        # サービスワーカー
        sw_path = static_dir / "sw.js"
        with open(sw_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_service_worker())

        # オフラインページ
        offline_path = static_dir.parent / "templates" / "offline.html"
        offline_path.parent.mkdir(parents=True, exist_ok=True)
        with open(offline_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_offline_page())

        # モバイル最適化CSS
        css_path = static_dir / "css" / "pwa-mobile.css"
        css_path.parent.mkdir(parents=True, exist_ok=True)
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_mobile_optimized_css())

        # アイコンディレクトリを作成
        icons_dir = static_dir / "icons"
        icons_dir.mkdir(exist_ok=True)

        self.logger.info(f"PWA files created in {static_dir}")

        return {
            "manifest": str(manifest_path),
            "service_worker": str(sw_path),
            "offline_page": str(offline_path),
            "mobile_css": str(css_path)
        }

    def register_service_worker_in_template(self, template_path: str) -> str:
        """テンプレートにサービスワーカーを登録"""
        registration_script = """
<!-- PWA Service Worker Registration -->
<script>
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);

                // アップデートチェック
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            // 新しいコンテンツが利用可能
                            if (confirm('New version available! Click OK to refresh and use the latest version.')) {
                                newWorker.postMessage({ type: 'SKIP_WAITING' });
                                window.location.reload();
                            }
                        }
                    });
                });
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}
</script>
"""

        return registration_script

# グローバルインスタンス
_pwa_manager = None

def get_pwa_manager() -> ProgressiveWebAppManager:
    """PWA管理システムのインスタンスを取得"""
    global _pwa_manager
    if _pwa_manager is None:
        _pwa_manager = ProgressiveWebAppManager()
    return _pwa_manager
