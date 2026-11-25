#!/bin/bash
# review.sh Body : renders every look in review/looks.json on that body -> review/<Body>_<k>.png
B=$1; cd /tmp/claude-0/ink
N=$(python3 -c "import json;print(len(json.load(open('review/looks.json'))))")
for k in $(seq 0 $((N-1))); do
  python3 -c "import json;json.dump(json.load(open('review/looks.json'))[$k]['map'],open('review/m_${B}_$k.json','w'))"
  /tmp/claude-0/bpyenv/bin/python preview_ink.py out5/NeonCoast_Ink.blend $B review/m_${B}_$k.json /tmp/claude-0/render/rv_${B}.glb >/dev/null 2>&1
  cd /tmp/claude-0/render
  node shotg.js rv_${B}_a.png "f=rv_${B}.glb&v=1.5708&d=10&y=4.4&w=500&h=800" 800 500 &
  node shotg.js rv_${B}_b.png "f=rv_${B}.glb&v=-1.5708&d=10&y=4.4&w=500&h=800" 800 500 &
  node shotg.js rv_${B}_c.png "f=rv_${B}.glb&v=front&d=9&y=1.6&w=500&h=800" 800 500 &
  node shotg.js rv_${B}_e.png "f=rv_${B}.glb&v=2.6&d=10&y=4.4&w=500&h=800" 800 500 &
  node shotg.js rv_${B}_d.png "f=rv_${B}.glb&v=-0.5&d=3.4&y=6.0&w=500&h=800" 800 500 &
  wait
  python3 -c "
from PIL import Image, ImageDraw
import json
ims=[Image.open('/tmp/claude-0/render/rv_${B}_'+v+'.png') for v in 'abcde']
o=Image.new('RGB',(2500,860),(30,30,30));[o.paste(im,(i*500,60)) for i,im in enumerate(ims)]
d=ImageDraw.Draw(o); n=json.load(open('/tmp/claude-0/ink/review/looks.json'))[$k]['names']
d.text((8,6),'  |  '.join(n[:5]),fill=(255,255,255)); d.text((8,30),'  |  '.join(n[5:]),fill=(255,255,255))
o.save('/tmp/claude-0/ink/review/${B}_$k.png')"
  cd /tmp/claude-0/ink
done
echo DONE $B
