"""ALKAN + BIRADLI: download product photos from the manufacturers' WooCommerce stores.
Codes never appear here: products are matched by sha1(folded code)[:12] listed in tools/want_store.txt."""
import hashlib, io, json, os, re, sys, time, unicodedata, urllib.request, builtins
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageChops
OUT = sys.argv[1] if len(sys.argv) > 1 else 'x'
LOG = open('tools/last_run_store.log', 'w')
def print(*a):
    builtins.print(*a); LOG.write(' '.join(map(str, a)) + '\n'); LOG.flush()
UA = {'User-Agent': 'Mozilla/5.0 (catalog image sync)'}
def get(u, tries=3):
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
        except Exception:
            if i == tries - 1: raise
            time.sleep(3 + 4 * i)
TR = str.maketrans('ÇĞİÖŞÜçğıöşü', 'CGIOSUcgiosu')
def fold(c):
    c = unicodedata.normalize('NFKC', c).replace('̇', '').translate(TR).upper()
    return re.sub(r'[^A-Z0-9]', '', c)
hs = lambda c: hashlib.sha1(fold(c).encode()).hexdigest()[:12]
def trim(im):
    bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
    box = ImageChops.difference(im, bg).convert('L').point(lambda v: 255 if v > 18 else 0).getbbox()
    if not box: return im
    pad = int(max(box[2] - box[0], box[3] - box[1]) * 0.05)
    return im.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad)))
want = set(l.strip() for l in open('tools/want_store.txt') if l.strip())
os.makedirs(f'img/{OUT}', exist_ok=True); os.makedirs(f'thumb/{OUT}', exist_ok=True)
galp = sys.argv[2] if len(sys.argv) > 2 else 'data/gal.json'
gal = json.load(open(galp)) if os.path.exists(galp) else {}
def listing(base):
    items, page = [], 1
    while True:
        try: j = json.loads(get(f'{base}/wp-json/wc/store/v1/products?per_page=100&page={page}'))
        except Exception as e: print('list fail', page, repr(e)); break
        if not j: break
        items += j; page += 1
    return items
found = {}
for base, kind in [('https://alkanzuccaciye.com', 'al'), ('https://biradli.com.tr', 'bi')]:
    items = listing(base); print(kind, 'store products', len(items))
    for it in items:
        if kind == 'al': codes = [it.get('sku') or '']
        else:
            codes = re.findall(r'\(([^()]*\d[^()]*)\)\s*$', it['name'].strip()) or [it.get('sku') or '']
        imgs = [x['src'] for x in it.get('images', [])]
        for c in codes:
            h = hs(c)
            if c and h in want and imgs and h not in found: found[h] = imgs
print('matched', len(found), 'of', len(want))
def work(h):
    if h in gal: return h, 0
    k = 0
    for u in found[h][:5]:
        try: im = trim(Image.open(io.BytesIO(get(u))).convert('RGB'))
        except Exception as e: continue
        k += 1
        b = im.copy(); b.thumbnail((1000, 1000), Image.LANCZOS); b.save(f'img/{OUT}/{h}-{k}.jpg', quality=84, optimize=True, progressive=True)
        t = im.copy(); t.thumbnail((420, 420), Image.LANCZOS); t.save(f'thumb/{OUT}/{h}-{k}.jpg', quality=80, optimize=True, progressive=True)
    return h, k
with ThreadPoolExecutor(8) as ex:
    for h, k in ex.map(work, list(found)):
        if k: gal[h] = k
json.dump(gal, open(galp, 'w'), separators=(',', ':'))
print('done', len(gal))
