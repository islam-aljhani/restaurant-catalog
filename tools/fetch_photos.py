"""Fetch product photos listed (as hashes) in tools/want.txt, resize, save to img/x and thumb/x."""
import hashlib, io, json, os, re, sys, time, urllib.request, builtins
LOG = open("tools/last_run.log", "w")
def print(*a):
    builtins.print(*a); LOG.write(" ".join(map(str, a)) + "\n"); LOG.flush()
from PIL import Image, ImageChops

def trim(im):
    bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
    diff = ImageChops.difference(im, bg).convert('L').point(lambda v: 255 if v > 18 else 0)
    box = diff.getbbox()
    if not box: return im
    w, h = box[2] - box[0], box[3] - box[1]; pad = int(max(w, h) * 0.05)
    return im.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad)))

H = lambda s: hashlib.sha1(s.encode()).hexdigest()[:12]
UA = {'User-Agent': 'Mozilla/5.0 (catalog image sync)'}
def get(u, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read()
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(2 + 3 * i)

want = set(l.strip() for l in open('tools/want.txt') if l.strip())
os.makedirs('img/x', exist_ok=True); os.makedirs('thumb/x', exist_ok=True)
gal_path = 'data/gal.json'
gal = json.load(open(gal_path)) if os.path.exists(gal_path) else {}
if os.path.exists('tools/redo'): gal = {}
try:
    sm = get('https://www.idfine.com.tr/sitemap.xml').decode('utf-8', 'ignore')
except Exception as e:
    print('sitemap fail', repr(e)); sm = ''
print('sitemap chars', len(sm))
skus = re.findall(r'<loc>https://www\.idfine\.com\.tr/urun/([^<]+)</loc>', sm)
todo = [s for s in skus if H(s) in want and H(s) not in gal]
print('to fetch', len(todo))
for n, sku in enumerate(todo, 1):
    h = H(sku)
    try:
        page = get(f'https://www.idfine.com.tr/urun/{sku}').decode('utf-8', 'ignore')
    except Exception as e:
        print(n, 'page fail', repr(e)); continue
    pg = re.sub(r'\\+/', '/', page).replace('&amp;', '&')
    hits = re.findall(r'cdn\.idfine\.com\.tr/products/(\d+)/([A-Za-z0-9_.\-]+?)\.(webp|jpg|jpeg|png)', pg)
    base = {}
    for folder, name, ext in hits:
        core = re.sub(r'_(small|medium|large|thumb)$', '', name)
        key = (folder, core, ext)
        base.setdefault(key, set()).add(name != core)
    og = re.search(r'property="og:image"\s+content="([^"]+)"', pg)
    urls = []
    if og and '/products/' in og.group(1): urls.append(og.group(1))
    for (folder, core, ext), sized in base.items():
        if True in sized:   # gallery images come in several sizes; related-product tiles do not
            u = f'https://cdn.idfine.com.tr/products/{folder}/{core}.{ext}'
            if u not in urls: urls.append(u)
    if n == 1: print('hits', len(hits), 'sample', hits[:4], 'og', og.group(1) if og else None)
    urls = urls[:5]
    if not urls: print(n, 'no gallery urls, page chars', len(page), page[:200].replace('\n',' '))
    k = 0
    for u in urls:
        try:
            im = trim(Image.open(io.BytesIO(get(u))).convert('RGB'))
        except Exception as e:
            print(n, 'img fail', e); continue
        k += 1
        big = im.copy(); big.thumbnail((1000, 1000), Image.LANCZOS)
        big.save(f'img/x/{h}-{k}.jpg', quality=84, optimize=True, progressive=True)
        sm_ = im.copy(); sm_.thumbnail((420, 420), Image.LANCZOS)
        sm_.save(f'thumb/x/{h}-{k}.jpg', quality=80, optimize=True, progressive=True)
    if k: gal[h] = k
    print(n, h, k)
    time.sleep(0.5)
json.dump(gal, open(gal_path, 'w'), separators=(',', ':'))
print('done', len(gal))
