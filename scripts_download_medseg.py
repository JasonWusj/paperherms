import os, requests, time
root='/root/paperhermes/import_papers/medical_segmentation'
sets={
 '01_baselines':[
  ('u-net','https://export.arxiv.org/pdf/1505.04597','unet_1505.04597.pdf'),
  ('3d-u-net','https://export.arxiv.org/pdf/1606.06650','3d_unet_1606.06650.pdf'),
  ('v-net','https://export.arxiv.org/pdf/1606.04797','vnet_1606.04797.pdf'),
  ('nnunet','https://export.arxiv.org/pdf/1809.10486','nnunet_1809.10486.pdf'),
  ('attention-u-net','https://export.arxiv.org/pdf/1804.03999','attention_unet_1804.03999.pdf'),
  ('unet-plus-plus','https://export.arxiv.org/pdf/1807.10165','unetpp_1807.10165.pdf'),
  ('kiu-net','https://export.arxiv.org/pdf/2006.04878','kiunet_2006.04878.pdf'),
 ],
 '02_transformers':[
  ('transunet','https://export.arxiv.org/pdf/2102.04306','transunet_2102.04306.pdf'),
  ('unetr','https://export.arxiv.org/pdf/2103.10504','unetr_2103.10504.pdf'),
  ('swin-unetr','https://export.arxiv.org/pdf/2201.01266','swin_unetr_2201.01266.pdf'),
  ('swin-unet','https://export.arxiv.org/pdf/2105.05537','swin_unet_2105.05537.pdf'),
  ('nnformer','https://export.arxiv.org/pdf/2109.03201','nnformer_2109.03201.pdf'),
  ('cotr','https://export.arxiv.org/pdf/2103.03024','cotr_2103.03024.pdf'),
  ('transbts','https://export.arxiv.org/pdf/2103.04430','transbts_2103.04430.pdf'),
  ('swin-transformer','https://export.arxiv.org/pdf/2103.14030','swin_transformer_2103.14030.pdf'),
 ],
 '03_loss_boundary':[
  ('generalised-dice','https://export.arxiv.org/pdf/1707.03237','generalised_dice_1707.03237.pdf'),
  ('boundary-loss','https://export.arxiv.org/pdf/1812.07032','boundary_loss_1812.07032.pdf'),
  ('hausdorff-loss','https://export.arxiv.org/pdf/1904.10030','hausdorff_loss_1904.10030.pdf'),
  ('focal-loss','https://export.arxiv.org/pdf/1708.02002','focal_loss_1708.02002.pdf'),
 ],
 '04_gaussian_heatmap_shape':[
  ('stacked-hourglass','https://export.arxiv.org/pdf/1603.06937','stacked_hourglass_1603.06937.pdf'),
  ('centernet','https://export.arxiv.org/pdf/1904.07850','centernet_1904.07850.pdf'),
  ('cornernet','https://export.arxiv.org/pdf/1808.01244','cornernet_1808.01244.pdf'),
 ],
 '05_datasets_metrics':[
  ('medical-segmentation-decathlon','https://export.arxiv.org/pdf/1902.09063','medical_segmentation_decathlon_1902.09063.pdf'),
  ('lits','https://export.arxiv.org/pdf/1901.04056','lits_1901.04056.pdf'),
 ]
}
headers={'User-Agent':'Mozilla/5.0 PaperHermes KB builder'}
for sub, items in sets.items():
    d=os.path.join(root, sub); os.makedirs(d, exist_ok=True)
    for key,url,fn in items:
        path=os.path.join(d, fn)
        if os.path.exists(path) and os.path.getsize(path)>100000:
            print('EXISTS', key, os.path.getsize(path), flush=True); continue
        ok=False
        for u in [url, url.replace('https://export.arxiv.org/pdf/','https://arxiv.org/pdf/')]:
            try:
                print('GET', key, u, flush=True)
                r=requests.get(u, timeout=300, stream=True, headers=headers, allow_redirects=True)
                r.raise_for_status()
                tmp=path+'.tmp'
                with open(tmp,'wb') as f:
                    for chunk in r.iter_content(1024*512):
                        if chunk: f.write(chunk)
                size=os.path.getsize(tmp)
                if size < 50000:
                    raise RuntimeError(f'too small {size}')
                os.replace(tmp,path)
                print('SAVED', key, size, path, flush=True); ok=True; break
            except Exception as e:
                print('ERR', key, repr(e), flush=True)
                try:
                    if os.path.exists(path+'.tmp'): os.remove(path+'.tmp')
                except Exception: pass
                time.sleep(2)
        if not ok:
            print('FAIL', key, path, flush=True)
print('DONE', flush=True)
