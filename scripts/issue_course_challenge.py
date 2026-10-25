"""Issue a baseline-bound public-family variation; it does not certify novelty."""
import argparse
import json
from app.course.assessment import issue_challenge

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--day',type=int,required=True,choices=range(12,27))
    args=parser.parse_args()
    print(json.dumps(issue_challenge(args.day),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
