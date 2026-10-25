"""双击start-course.cmd调用：复用现有服务或在回环地址启动课程页面。"""
from pathlib import Path
import subprocess
import sys
import time
import webbrowser
import httpx

ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8012'


def ready():
    try:
        r=httpx.get(URL+'/api/course',timeout=1,trust_env=False)
        return r.status_code==200 and len(r.json().get('lessons',[]))==26
    except (httpx.HTTPError,ValueError):
        return False


def main():
    if not ready():
        directory=ROOT/'tmp';directory.mkdir(exist_ok=True)
        with (directory/'course-launch.log').open('a',encoding='utf-8') as log:
            flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
            process=subprocess.Popen([sys.executable,'-m','uvicorn','app.leave_web:app','--host','127.0.0.1','--port','8012','--timeout-graceful-shutdown','5'],cwd=ROOT,stdout=log,stderr=log,creationflags=flags)
        (directory/'course-launch.pid').write_text(str(process.pid),encoding='utf-8')
        for _ in range(40):
            if ready():break
            if process.poll() is not None:break
            time.sleep(0.25)
    if not ready():
        print('课程服务未启动，请检查tmp/course-launch.log和requirements/course-runtime.txt。未停止其他进程。')
        return 1
    webbrowser.open(URL+'/course')
    print('课程已打开。业务实验还需要Docker/PostgreSQL启动。')
    return 0


if __name__=='__main__':raise SystemExit(main())
