import os, requests, sys, time
root='/root/paperhermes/import_papers/medical_segmentation'
base='http://127.0.0.1:8000'
existing=requests.get(base+'/api/papers', timeout=30).json()
existing_files={p.get('original_filename') for p in existing}
print('EXISTING', len(existing_files), sorted([x for x in existing_files if x])[:20], flush=True)
paths=[]
for dirpath, _, files in os.walk(root):
    for f in files:
        if f.endswith('.pdf'):
            paths.append(os.path.join(dirpath,f))
paths=sorted(paths)
print('FOUND_PDFS', len(paths), flush=True)
for path in paths:
    fn=os.path.basename(path)
    if fn in existing_files:
        print('SKIP_EXISTS', fn, flush=True)
        continue
    size=os.path.getsize(path)
    if size < 50000:
        print('SKIP_SMALL', fn, size, flush=True)
        continue
    print('UPLOAD', fn, size, flush=True)
    try:
        with open(path,'rb') as f:
            r=requests.post(base+'/api/papers', files={'file':(fn,f,'application/pdf')}, timeout=900)
        print('STATUS', fn, r.status_code, r.text[:500].replace('\n',' '), flush=True)
    except Exception as e:
        print('ERROR', fn, repr(e), flush=True)
    time.sleep(2)
print('IMPORT_DONE', flush=True)
