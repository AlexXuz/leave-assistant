"""Read evidence and prerequisite gates; never mark a learner complete from reference checks."""
import argparse
import json
from app.course.assessment import assess_day

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--day',type=int,choices=range(1,27))
    args=parser.parse_args()
    days=[args.day] if args.day else range(1,27)
    print(json.dumps([assess_day(day) for day in days],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
