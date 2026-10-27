"""Pioli: match product pages by (collection, article code) hashes in tools/want_pioli.txt."""
import hashlib, io, json, os, re, time, urllib.request, builtins, html as H
from PIL import Image, ImageChops
LOG = open('tools/last_run_pioli.log', 'w')
def print(*a):
    builtins.print(*a); LOG.write(' '.join(map(str, a)) + '\n'); LOG.flush()
hs = lambda s: hashlib.sha1(s.encode()).hexdigest()[:12]
norm = lambda s: re.sub(r'\s+', ' ', H.unescape(s)).strip().upper()
UA = {'User-Agent': 'Mozilla/5.0 (catalog image sync)'}
def get(u, tries=3):
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read()
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 + 3 * i)
def trim(im):
    bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
    box = ImageChops.difference(im, bg).convert('L').point(lambda v: 255 if v > 18 else 0).getbbox()
    if not box: return im
    pad = int(max(box[2] - box[0], box[3] - box[1]) * 0.05)
    return im.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad)))
want = set(l.strip() for l in open('tools/want_pioli.txt') if l.strip())
os.makedirs('img/x', exist_ok=True); os.makedirs('thumb/x', exist_ok=True)
gal = json.load(open('data/gal.json')) if os.path.exists('data/gal.json') else {}
urls = []
try:
    idx = get('https://pioli.co/sitemap_index.xml').decode('utf-8', 'ignore')
    maps = [m for m in re.findall(r'<loc>([^<]+)</loc>', idx) if 'product-sitemap' in m]
except Exception as e:
    print('index fail', repr(e)); maps = ['https://pioli.co/product-sitemap.xml']
for m in maps:
    try: urls += [u for u in re.findall(r'<loc>([^<]+)</loc>', get(m).decode('utf-8', 'ignore')) if '/product/' in u]
    except Exception as e: print('map fail', m, repr(e))
print('product pages', len(urls))
from concurrent.futures import ThreadPoolExecutor
def page(u):
    try: return u, get(u).decode('utf-8', 'ignore')
    except Exception as e: return u, None
done = 0
with ThreadPoolExecutor(8) as ex:
    for n, (u, pg) in enumerate(ex.map(page, urls), 1):
        if pg is None: print(n, 'page fail', u); continue
        code = re.search(r'Article Code\s*:\s*([A-Z0-9]+)', pg)
        if not code: continue
        cats = [norm(c) for c in re.findall(r'/product-category/[^"]+"[^>]*rel="tag">([^<]+)</a>', pg)]
        keys = [hs(c + '|' + code.group(1)) for c in cats]
        keys = [k for k in keys if k in want and k not in gal]
        if not keys: continue
        imgs = []
        for x in re.findall(r'data-large_image="([^"]+)"', pg):
            if x not in imgs: imgs.append(x)
        k = 0
        for x in imgs[:5]:
            try: im = trim(Image.open(io.BytesIO(get(x))).convert('RGB'))
            except Exception as e: print(n, 'img fail', repr(e)); continue
            k += 1
            b = im.copy(); b.thumbnail((1000, 1000), Image.LANCZOS); b.save(f'img/x/{keys[0]}-{k}.jpg', quality=84, optimize=True, progressive=True)
            t = im.copy(); t.thumbnail((420, 420), Image.LANCZOS); t.save(f'thumb/x/{keys[0]}-{k}.jpg', quality=80, optimize=True, progressive=True)
        if k:
            for kk in keys:
                gal[kk] = k if kk == keys[0] else keys[0] + ':' + str(k)
            done += 1
        print(n, code.group(1), cats[:2], k)
json.dump(gal, open('data/gal.json', 'w'), separators=(',', ':'))
print('done', done, len(gal))
