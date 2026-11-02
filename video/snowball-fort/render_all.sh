#!/bin/bash
cd ${SCRATCH:-$(pwd)}
for sh in s01 s02 s03 s04 s05 s06 s07 s08 s09 s10 s11 s12 s13 s14 s15; do
  if [ -f ${SCRATCH:-$(pwd)}/rend/$sh/.done ]; then continue; fi
  st=$(date +%s)
  python3 /home/user/wda-builder/video/snowball-fort/scenes.py $sh ${SCRATCH:-$(pwd)}/rend anim 16 0.75 > ${SCRATCH:-$(pwd)}/rlog_$sh.txt 2>&1 && touch ${SCRATCH:-$(pwd)}/rend/$sh/.done
  echo "$sh $(( $(date +%s)-st ))s $(ls ${SCRATCH:-$(pwd)}/rend/$sh/*.png 2>/dev/null | wc -l) frames" 
done
echo ALLDONE
