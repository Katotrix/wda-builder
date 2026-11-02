import sys, numpy as np, soundfile as sf
sr=48000; bpm=112; beat=60/bpm; dur=float(sys.argv[2]); N=int(dur*sr)
rng=np.random.default_rng(3)
L=np.zeros(N); R=np.zeros(N)
def add(sig, t, pan=0.0, g=1.0):
    i=int(t*sr); j=min(N,i+len(sig))
    if i>=N: return
    L[i:j]+=sig[:j-i]*g*(1-pan)/1; R[i:j]+=sig[:j-i]*g*(1+pan)/1
def f(n): return 440*2**((n-69)/12)
def pluck(n, d=0.35):
    t=np.arange(int(d*sr))/sr; fr=f(n)
    s=(np.sin(2*np.pi*fr*t)+0.35*np.sin(4*np.pi*fr*t)+0.12*np.sin(6*np.pi*fr*t))
    return s*np.exp(-t*9)*(1-np.exp(-t*800))
def glock(n):
    t=np.arange(int(1.2*sr))/sr; fr=f(n)
    return (np.sin(2*np.pi*fr*t)+0.4*np.sin(2*np.pi*fr*2.76*t)*np.exp(-t*6))*np.exp(-t*3.5)
def bass(n,d):
    t=np.arange(int(d*sr))/sr; fr=f(n)
    return np.tanh(1.5*np.sin(2*np.pi*fr*t))*np.exp(-t*3)*(1-np.exp(-t*300))
def kick():
    t=np.arange(int(0.3*sr))/sr; ph=2*np.pi*np.cumsum(50+90*np.exp(-t*30))/sr
    return np.sin(ph)*np.exp(-t*12)
def hat():
    t=np.arange(int(0.05*sr))/sr; s=rng.standard_normal(len(t)); s=np.diff(s,prepend=0)
    return s*np.exp(-t*90)
def snap():
    t=np.arange(int(0.15*sr))/sr; s=rng.standard_normal(len(t))
    return (s*0.6+np.sin(2*np.pi*190*t))*np.exp(-t*30)
# chords: C, Am, F, G  (I vi IV V) in C major
prog=[(48,[60,64,67]),(45,[57,60,64]),(41,[57,60,65]),(43,[59,62,67])]
mel=[72,76,79,76, 74,72,69,72, 77,76,72,69, 71,74,79,74]
bar=4*beat; t0=0.0; b=0
while t0<dur:
    root,ch=prog[b%4]
    add(bass(root,beat*1.8),t0,0,0.45); add(bass(root,beat*1.8),t0+2*beat,0,0.4)
    for k in range(8):  # eighth-note pizzicato arpeggio
        add(pluck(ch[[0,1,2,1,0,2,1,2][k]]+12*(k%2==1)), t0+k*beat/2, pan=(-0.4 if k%2 else 0.4), g=0.22)
    if b>=1:
        for k in range(4):
            add(kick(),t0+k*beat,0,0.55 if k in(0,2) else 0.0)
            if k in(1,3): add(snap(),t0+k*beat,0,0.22)
            add(hat(),t0+k*beat+beat/2,0.2,0.12)
    if b>=2:
        for k in range(4):
            if (b+k)%2==0: add(glock(mel[(b%4)*4+k]+12),t0+k*beat,-0.3,0.08)
    t0+=bar; b+=1
m=np.stack([L,R],1)
# fade in/out
fi=int(0.3*sr); fo=int(1.5*sr); m[:fi]*=np.linspace(0,1,fi)[:,None]; m[-fo:]*=np.linspace(1,0,fo)[:,None]
m/=np.abs(m).max()*1.1
sf.write(sys.argv[1]+"/music.wav", m.astype(np.float32), sr)
# whoosh sfx
t=np.arange(int(0.55*sr))/sr; n=rng.standard_normal(len(t))
env=np.sin(np.pi*np.clip(t/0.55,0,1))**2
from numpy.fft import rfft, irfft
# moving band-ish via simple one-pole lowpass with sweeping cutoff
y=np.zeros_like(n); s=0
for i in range(len(n)):
    a=0.02+0.25*env[i]; s+=a*(n[i]-s); y[i]=s
y=y*env; y/=np.abs(y).max()
sf.write(sys.argv[1]+"/whoosh.wav", np.stack([y*0.9,y],1).astype(np.float32), sr)
print("ok")
