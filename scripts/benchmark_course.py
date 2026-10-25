"""只测本机已登录GET接口，不调用模型；不代表生产或LLM性能。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import math
import time
from urllib.parse import urlsplit
import httpx
from app.pgvector_store import PROJECT_ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8012')
    parser.add_argument('--samples',type=int,default=20)
    parser.add_argument('--concurrency',type=int,default=2)
    args=parser.parse_args()
    if urlsplit(args.url).hostname not in {'127.0.0.1','localhost'} or not 10<=args.samples<=100 or not 1<=args.concurrency<=8:
        parser.error('仅支持回环地址，10–100样本，1–8并发')
    with httpx.Client(base_url=args.url,timeout=10,trust_env=False) as client:
        origin={'Origin':args.url}
        client.post('/api/login',headers=origin,json={'username':'zhangsan','password':'demo123'}).raise_for_status()
        try:
            client.get('/api/me').raise_for_status()
            def one(_):
                start=time.perf_counter();response=client.get('/api/me')
                return {'ms':1000*(time.perf_counter()-start),'status':response.status_code}
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                results=list(pool.map(one,range(args.samples)))
        finally:
            client.post('/api/logout',headers=origin,json={})
    durations=sorted(r['ms'] for r in results)
    report={'endpoint':'GET /api/me','environment':'local_loopback','samples':args.samples,'concurrency':args.concurrency,'warmup_requests':1,
            'chat_model_called':False,'success_rate':sum(r['status']==200 for r in results)/len(results),
            'p50_ms':round(durations[math.ceil(.50*len(results))-1],2),'p95_ms':round(durations[math.ceil(.95*len(results))-1],2),
            'limitations':'Small local authenticated SQL-read sample; not LLM latency, load capacity or production SLA.'}
    path=PROJECT_ROOT/'reports'/f"course-benchmark-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));print(path)


if __name__=='__main__':main()
