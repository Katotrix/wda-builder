import sys, json, numpy as np, soundfile as sf
S=sys.argv[1]; sr=48000
sp=json.load(open(S+"/spans.json")); shots=json.load(open(S+"/shots.json"))
N=int((sp["total"]+0.5)*sr); out=np.zeros((N,2))
wh,_=sf.read(S+"/whoosh.wav")
rng=np.random.default_rng(1)
def put(sig,t,g):
    i=int(t*sr)-len(sig)//2; i=max(i,0); j=min(N,i+len(sig)); out[i:j]+=sig[:j-i]*g
# whoosh on whip transitions, soft shimmer on flash transitions
t=np.arange(int(0.6*sr))/sr
shimmer=sum(np.sin(2*np.pi*f*t)*np.exp(-t*6) for f in (1568,2093,2637,3136))/4
shimmer=np.stack([shimmer,shimmer],1)
for sid,st,en in sp["spans"][1:]:
    if shots[sid].get("tr")=="whip": put(wh,st,0.35)
    else: put(shimmer*np.linspace(0,1,len(shimmer))[:,None]**0.1,st+0.05,0.12)
# splat at the hit (start of s15) and stretch creak during s13
tt=np.arange(int(0.35*sr))/sr; n=rng.standard_normal(len(tt))
y=np.zeros_like(n); s=0
for i in range(len(n)): s+=0.15*(n[i]-s); y[i]=s
splat=(y/np.abs(y).max())*np.exp(-tt*12)+0.6*np.sin(2*np.pi*90*tt)*np.exp(-tt*25)
put(np.stack([splat,splat],1), [s for s in sp["spans"] if s[0]=="s15"][0][1]+0.05, 0.8)
tt=np.arange(int(1.0*sr))/sr; creak=np.sin(2*np.pi*(180+120*tt)*tt + 3*np.sin(2*np.pi*13*tt))*0.3*np.minimum(tt*5,1)*np.exp(-tt*1.5)
put(np.stack([creak,creak],1), [s for s in sp["spans"] if s[0]=="s13"][0][1]+1.2, 0.25)
sf.write(S+"/sfx.wav",out.astype(np.float32),sr); print("sfx ok")
