"""受信任宿主调用的只读脚本，stdout仅输出JSON。"""
import json
import os
from pathlib import Path
from app.course.reporting import department_report

if __name__=='__main__':
    result=department_report(os.environ['COURSE_REPORT_RUN'],os.environ['COURSE_REPORT_USER'])
    template=Path(__file__).resolve().parents[1]/'assets/report.md'
    print(json.dumps({'data':result,'markdown':template.read_text(encoding='utf-8').format(**result)},ensure_ascii=False))
