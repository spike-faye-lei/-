"""天团控制台 · 桌面 App 壳（单进程）
开发态: py app.py —— 线程里起 FastAPI(127.0.0.1:8777)，pywebview 开原生窗口
打包态: PyInstaller onefile exe —— backend/frontend 从 _MEIPASS 加载，数据存 %LOCALAPPDATA%
端口被占（后端已在跑）则直接复用。无 pywebview 时退回浏览器。
"""
import os
import sys
import threading
import time
import ctypes
import traceback
import urllib.request

PORT = int(os.environ.get("TEAM_CONSOLE_PORT", "8777"))
URL = f"http://127.0.0.1:{PORT}"
HERE = os.path.dirname(os.path.abspath(__file__))
RES = getattr(sys, "_MEIPASS", HERE)  # PyInstaller onefile 解包目录
LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", HERE), "TeamConsole")
LOG_FILE = os.path.join(LOG_DIR, "startup.log")
MUTEX_NAME = "Local\\TeamConsole-" + str(PORT)

def log(msg):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def alert(title, msg):
    try:
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
    except Exception:
        pass


def open_browser_fallback(reason="", keep_alive=True):
    log("使用浏览器打开" + (f"（{reason}）" if reason else ""))
    import webbrowser
    webbrowser.open(URL)
    while keep_alive:
        time.sleep(3600)



def backend_up():
    try:
        urllib.request.urlopen(f"{URL}/api/health", timeout=2)
        return True
    except Exception:
        return False


def start_backend_thread():
    log("后端模块导入中...")
    try:
        sys.path.insert(0, RES)
        from backend import main as backend_main
        import uvicorn
    except Exception as e:
        log("后端导入失败:\n" + traceback.format_exc())
        alert("天团控制台", "后端导入失败，详见 startup.log")
        raise
    log("后端模块导入完成")
    def _run_backend():
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")
        try:
            uvicorn.run(backend_main.app, host="127.0.0.1",
                            port=PORT, log_level="warning")
        except Exception:
            log("uvicorn 启动失败:\n" + traceback.format_exc())
            alert("天团控制台", "uvicorn 启动失败，详见 startup.log")
    t = threading.Thread(target=_run_backend, daemon=True)
    t.start()
    log("uvicorn 线程已启动，等待后端健康检查...")
    for _ in range(40):
        if backend_up():
            return True
        time.sleep(0.5)
    return False


def main():
    # 防止双击快捷方式时“无声无息”：重复实例不再直接退出，而是打开浏览器指向已有服务。
    if sys.platform == "win32":
        try:
            mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                log("检测到已有实例，打开浏览器复用现有服务")
                open_browser_fallback("已有实例", keep_alive=False)
                return
        except Exception as e:
            log("单实例检测失败: %s" % e)

    log("启动开始")
    try:
        if not backend_up() and not start_backend_thread():
            log("后端启动失败")
            alert("天团控制台", "后端启动失败，详见 startup.log")
            sys.exit(1)
        log("后端已就绪")

        try:
            import webview  # pywebview
            webview.create_window("天团控制台", URL,
                                  width=1360, height=880, min_size=(1000, 640),
                                  background_color="#ffffff")
            log("pywebview 窗口已创建")
            webview.start()
        except ImportError:
            log("pywebview 未安装")
            open_browser_fallback("未安装 pywebview")
        except Exception as e:
            log("pywebview 启动失败: %s" % e)
            open_browser_fallback("pywebview 启动失败")
    except SystemExit:
        raise
    except Exception:
        log("未捕获异常:\n" + traceback.format_exc())
        alert("天团控制台", "启动异常，详见 startup.log")
        open_browser_fallback("启动异常")
    # if not backend_up() and not start_backend_thread():
        # print("后端启动失败")
        # sys.exit(1)
if False:
    try:
        # import webview  # pywebview
        webview.create_window("天团控制台", URL,
                              width=1360, height=880, min_size=(1000, 640),
                              background_color="#ffffff")
        webview.start()
    except ImportError:
        import webbrowser
        print("pywebview 未安装，用浏览器打开…")
        webbrowser.open(URL)
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
