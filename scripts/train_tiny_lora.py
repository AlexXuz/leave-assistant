"""Day21 CPU真实LoRA机制实验；随机初始化小模型，不宣称改善真实业务LLM。"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import time

import torch
from transformers import GPT2Config, GPT2LMHeadModel
from peft import LoraConfig, PeftModel, get_peft_model

from app.pgvector_store import PROJECT_ROOT
from app.course.examples.optimization_strategy import validate_splits
from app.course.examples.sft_labels import build_labels

ALPHABET='\n '+''.join(chr(i) for i in range(33,127))
VOCAB={char:i+1 for i,char in enumerate(ALPHABET)}
PAD=0


def base_model():
    torch.manual_seed(42)
    config=GPT2Config(vocab_size=len(VOCAB)+1,n_positions=128,n_ctx=128,n_embd=48,n_layer=1,n_head=2,
                      resid_pdrop=0,embd_pdrop=0,attn_pdrop=0,bos_token_id=PAD,eos_token_id=VOCAB['\n'],pad_token_id=PAD)
    return GPT2LMHeadModel(config)


def encode(row):
    prompt='intent: '+row['input']+'\nanswer: '
    text=prompt+row['output']+'\n'
    ids=[VOCAB[c] for c in text]
    if len(ids)>128:
        raise ValueError('样本超过微型模型容量')
    padded=ids+[PAD]*(128-len(ids))
    return padded,build_labels(padded,len(prompt),len(ids))


def run(steps=60):
    if not 1<=steps<=300:
        raise ValueError('步数范围1至300')
    torch.set_num_threads(2)
    rows=[json.loads(line) for line in (PROJECT_ROOT/'course/fixtures/sft_intents.jsonl').read_text(encoding='utf-8').splitlines()]
    split=validate_splits(rows)
    groups={name:[encode(r) for r in rows if r['split']==name] for name in split}
    def batch(name):
        values=groups[name]
        return torch.tensor([r[0] for r in values]),torch.tensor([r[1] for r in values])
    base=base_model()
    model=get_peft_model(base,LoraConfig(task_type='CAUSAL_LM',r=4,lora_alpha=8,lora_dropout=0,target_modules=['c_attn','c_proj'],fan_in_fan_out=True,bias='none'))
    frozen={n:p.detach().clone() for n,p in model.named_parameters() if not p.requires_grad}
    trainable={n:p.detach().clone() for n,p in model.named_parameters() if p.requires_grad}
    def loss(name):
        model.eval()
        ids,labels=batch(name)
        with torch.no_grad():
            return float(model(input_ids=ids,attention_mask=(ids!=PAD).long(),labels=labels).loss)
    before={name:loss(name) for name in groups}
    optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=0.02)
    ids,labels=batch('train')
    started=time.perf_counter()
    curve=[]
    for step in range(steps):
        model.train();optimizer.zero_grad()
        value=model(input_ids=ids,attention_mask=(ids!=PAD).long(),labels=labels).loss
        value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step()
        if step%10==0 or step==steps-1:
            curve.append({'step':step+1,'train_loss':float(value.detach())})
    after={name:loss(name) for name in groups}
    parameters=dict(model.named_parameters())
    unchanged=all(torch.equal(p,parameters[n]) for n,p in frozen.items())
    changed=any(not torch.equal(p,parameters[n]) for n,p in trainable.items())
    output=PROJECT_ROOT/'tmp/course/tiny-lora'
    output.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(output)
    ids,labels=batch('test');model.eval()
    with torch.no_grad():
        expected=model(input_ids=ids,attention_mask=(ids!=PAD).long()).logits
    reloaded=PeftModel.from_pretrained(base_model(),output);reloaded.eval()
    with torch.no_grad():
        actual=reloaded(input_ids=ids,attention_mask=(ids!=PAD).long()).logits
    reload_match=torch.allclose(expected,actual,atol=1e-5)
    result={'experiment':'tiny_random_gpt2_peft_lora_cpu','seed':42,'device':'cpu','steps':steps,'seconds':round(time.perf_counter()-started,3),
            'splits':split,'loss_before':before,'loss_after':after,'curve':curve,'frozen_base_unchanged':unchanged,'adapter_changed':changed,
            'adapter_reload_matches':reload_match,'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad),
            'total_parameters':sum(p.numel() for p in model.parameters()),'output_directory':'tmp/course/tiny-lora',
            'limitations':'Random base, tiny synthetic English intent examples, mechanism verification only; no pretrained-model task-quality claim.'}
    assert unchanged and changed and reload_match
    report=PROJECT_ROOT/'reports'/f"course-lora-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result,report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--steps',type=int,default=60)
    args=parser.parse_args();result,path=run(args.steps)
    print(json.dumps(result,ensure_ascii=False,indent=2));print(path)
