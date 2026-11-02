import sys, json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
S=sys.argv[1]
k = Kokoro(S+"/voice/kokoro.onnx", S+"/voice/voices.bin")
lines=json.load(open(S+"/script.json"))
out=[]; t=0.35; sr=24000; timing=[]
out.append(np.zeros(int(0.35*sr),dtype=np.float32))
for i,l in enumerate(lines):
    a, sr = k.create(l["text"], voice="am_michael", speed=1.18, lang="en-us")
    # trim silence
    thr=0.01; idx=np.where(np.abs(a)>thr)[0]; a=a[max(idx[0]-240,0):idx[-1]+480]
    d=len(a)/sr
    gap=0.10 if i+1<len(lines) and lines[i+1]["shot"]==l["shot"] else 0.18
    timing.append({**l,"start":round(t,3),"end":round(t+d,3)})
    out+= [a, np.zeros(int(gap*sr),dtype=np.float32)]; t+=d+gap
out.append(np.zeros(int(0.8*sr),dtype=np.float32))
sf.write(S+"/vo.wav", np.concatenate(out), sr)
json.dump(timing, open(S+"/timing.json","w"), indent=1)
print("total", t+0.8)
