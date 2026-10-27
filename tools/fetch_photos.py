"""Fetch product photos listed (as hashes) in tools/want.txt, resize, save to img/x and thumb/x."""
import hashlib, io, json, os, re, sys, time, urllib.request
from PIL import Image

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
sm = get('https://www.idfine.com.tr/sitemap.xml').decode('utf-8', 'ignore')
skus = re.findall(r'<loc>https://www\.idfine\.com\.tr/urun/([^<]+)</loc>', sm)
todo = [s for s in skus if H(s) in want and H(s) not in gal]
print('to fetch', len(todo))
for n, sku in enumerate(todo, 1):
    h = H(sku)
    try:
        page = get(f'https://www.idfine.com.tr/urun/{sku}').decode('utf-8', 'ignore')
    except Exception as e:
        print(n, 'page fail', e); continue
    med = re.findall(r'https://cdn\.idfine\.com\.tr/products/\d+/[^"\'\s)]+?_medium\.webp', page)
    urls = []
    for m in med:
        u = m.replace('_medium.webp', '.webp')
        if u not in urls: urls.append(u)
    urls = urls[:5]
    k = 0
    for u in urls:
        try:
            im = Image.open(io.BytesIO(get(u))).convert('RGB')
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
