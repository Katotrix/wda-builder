import sys, json, os, re, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
S=sys.argv[1]; OUT=sys.argv[2]; W,H,FPS=720,1280,30
timing=json.load(open(S+"/timing.json")); shots=json.load(open(S+"/shots.json"))
TOTAL=timing[-1]["end"]+0.9
# shot spans
order=[]; 
for l in timing:
    if not order or order[-1][0]!=l["shot"]: order.append([l["shot"],l["start"]])
spans=[]
for i,(sid,st) in enumerate(order):
    st=0 if i==0 else st-0.08
    en=order[i+1][1]-0.08 if i+1<len(order) else TOTAL
    spans.append((sid,st,en))
# captions: split lines into 1-3 word chunks
caps=[]
for l in timing:
    words=l["text"].split(); chunks=[]; cur=[]
    for w in words:
        cur.append(w)
        if len(cur)>=3 or w.endswith(",") or (len(cur)==2 and len(" ".join(cur))>14):
            chunks.append(cur); cur=[]
    if cur:
        if len(cur)==1 and chunks and len(chunks[-1])<3: chunks[-1]+=cur
        else: chunks.append(cur)
    lens=[sum(len(w) for w in c)+2 for c in chunks]; tot=sum(lens); t=l["start"]
    for c,n in zip(chunks,lens):
        d=(l["end"]-l["start"])*n/tot
        caps.append((t, t+d, re.sub(r"[,.]$","", " ".join(c)).rstrip(",.")))
        t+=d
# extend caption to next caption start
caps=[(a, caps[i+1][0] if i+1<len(caps) else b+0.5, s) for i,(a,b,s) in enumerate(caps)]
font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",40)
capcache={}
def caption(text):
    if text in capcache: return capcache[text]
    im=Image.new("RGBA",(W,200),(0,0,0,0)); d=ImageDraw.Draw(im)
    tw=d.textlength(text,font=font); x=(W-tw)/2
    sh=Image.new("RGBA",(W,200),(0,0,0,0)); ds=ImageDraw.Draw(sh)
    ds.text((x+2,72),text,font=font,fill=(0,0,0,170),stroke_width=3,stroke_fill=(0,0,0,150))
    sh=sh.filter(ImageFilter.GaussianBlur(4))
    d.text((x,70),text,font=font,fill=(255,255,255,255),stroke_width=2,stroke_fill=(10,10,10,255))
    out=Image.alpha_composite(sh,im); capcache[text]=out; return out
def ease(x): x=min(max(x,0),1); return x*x*(3-2*x)
imgcache={}
def src(sid):
    if sid not in imgcache:
        p=S+"/img/"+shots[sid]["file"]
        if os.path.exists(p): im=Image.open(p).convert("RGB")
        else:
            g=np.zeros((1080,1920,3),np.uint8); g[:]= (40,150,190); im=Image.fromarray(g)
            ImageDraw.Draw(im).text((900,500),sid,fill="white")
        imgcache[sid]=im
    return imgcache[sid]
def view(sid,u):
    """u in [0,1] progress through shot -> 720x1280 frame"""
    sh=shots[sid]; im=src(sid); iw,ih=im.size
    e=ease(u) if sh.get("ease",True) else u
    z=sh["z"][0]+(sh["z"][1]-sh["z"][0])*e
    cx=sh["x"][0]+(sh["x"][1]-sh["x"][0])*e; cy=sh["y"][0]+(sh["y"][1]-sh["y"][0])*e
    ch=ih/z; cw=ch*W/H
    if cw>iw: cw=iw; ch=cw*H/W
    x0=min(max(cx*iw-cw/2,0),iw-cw); y0=min(max(cy*ih-ch/2,0),ih-ch)
    return im.resize((W,H),Image.BICUBIC,box=(x0,y0,x0+cw,y0+ch))
def at(t):
    for i,(sid,st,en) in enumerate(spans):
        if st<=t<en or i==len(spans)-1: return i
TR=0.32
proc=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
  "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",OUT],stdin=subprocess.PIPE)
nf=int(TOTAL*FPS)
for f in range(nf):
    t=f/FPS; i=at(t); sid,st,en=spans[i]
    fr=view(sid,(t-st)/(en-st))
    # transition into next shot
    if i+1<len(spans) and en-t<TR/2 or i>0 and t-st<TR/2:
        if en-t<TR/2 and i+1<len(spans): k=i+1; d=(TR/2-(en-t))/TR  # 0..0.5 before cut
        else: k=i; d=0.5+(t-st)/TR
        kind=shots[spans[k][0]].get("tr","flash")
        if kind=="flash":
            a=1-abs(d-0.5)*2   # 0->1 at cut ->0
            bl=fr.filter(ImageFilter.GaussianBlur(10*a))
            arr=np.asarray(bl).astype(np.float32)
            arr=arr+(255-arr)*(a**1.5)*0.85
            fr=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
        else: # whip pan
            a=1-abs(d-0.5)*2; off=int((d-0.5)*W*0.9)
            arr=np.asarray(fr); arr=np.roll(arr, -off if d<0.5 else -off, axis=1)
            fr=Image.fromarray(arr).filter(ImageFilter.BoxBlur(int(2+22*a)))
    for a,b,s in caps:
        if a<=t<b:
            c=caption(s); pop=min(1,(t-a)/0.08)
            if pop<1:
                sc=0.85+0.15*pop; cc=c.resize((int(W*sc),int(200*sc)))
                fr.paste(cc,((W-cc.width)//2, 930+(200-cc.height)//2),cc)
            else: fr.paste(c,(0,930),c)
            break
    proc.stdin.write(fr.convert("RGB").tobytes())
proc.stdin.close(); proc.wait()
json.dump({"spans":spans,"total":TOTAL},open(S+"/spans.json","w"))
print("frames",nf)
