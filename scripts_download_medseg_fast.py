import os, subprocess, sys
root='/root/paperhermes/import_papers/medical_segmentation'
items=[
 ('01_baselines','unetpp_1807.10165.pdf','https://export.arxiv.org/pdf/1807.10165'),
 ('01_baselines','kiunet_2006.04878.pdf','https://export.arxiv.org/pdf/2006.04878'),
 ('02_transformers','transunet_2102.04306.pdf','https://export.arxiv.org/pdf/2102.04306'),
 ('02_transformers','unetr_2103.10504.pdf','https://export.arxiv.org/pdf/2103.10504'),
 ('02_transformers','swin_unetr_2201.01266.pdf','https://export.arxiv.org/pdf/2201.01266'),
 ('02_transformers','swin_unet_2105.05537.pdf','https://export.arxiv.org/pdf/2105.05537'),
 ('02_transformers','nnformer_2109.03201.pdf','https://export.arxiv.org/pdf/2109.03201'),
 ('02_transformers','cotr_2103.03024.pdf','https://export.arxiv.org/pdf/2103.03024'),
 ('02_transformers','transbts_2103.04430.pdf','https://export.arxiv.org/pdf/2103.04430'),
 ('02_transformers','swin_transformer_2103.14030.pdf','https://export.arxiv.org/pdf/2103.14030'),
 ('03_loss_boundary','generalised_dice_1707.03237.pdf','https://export.arxiv.org/pdf/1707.03237'),
 ('03_loss_boundary','boundary_loss_1812.07032.pdf','https://export.arxiv.org/pdf/1812.07032'),
 ('03_loss_boundary','hausdorff_loss_1904.10030.pdf','https://export.arxiv.org/pdf/1904.10030'),
 ('03_loss_boundary','focal_loss_1708.02002.pdf','https://export.arxiv.org/pdf/1708.02002'),
 ('04_gaussian_heatmap_shape','stacked_hourglass_1603.06937.pdf','https://export.arxiv.org/pdf/1603.06937'),
 ('04_gaussian_heatmap_shape','centernet_1904.07850.pdf','https://export.arxiv.org/pdf/1904.07850'),
 ('04_gaussian_heatmap_shape','cornernet_1808.01244.pdf','https://export.arxiv.org/pdf/1808.01244'),
 ('05_datasets_metrics','medical_segmentation_decathlon_1902.09063.pdf','https://export.arxiv.org/pdf/1902.09063'),
 ('05_datasets_metrics','lits_1901.04056.pdf','https://export.arxiv.org/pdf/1901.04056'),
]
for sub,fn,url in items:
    d=os.path.join(root,sub); os.makedirs(d,exist_ok=True)
    path=os.path.join(d,fn)
    if os.path.exists(path) and os.path.getsize(path)>100000:
        print('EXISTS', fn, os.path.getsize(path), flush=True); continue
    tmp=path+'.tmp'
    for u in [url, url.replace('https://export.arxiv.org/pdf/','https://arxiv.org/pdf/')]:
        print('CURL', fn, u, flush=True)
        try:
            subprocess.run(['curl','-L','--fail','--connect-timeout','20','--max-time','120','--retry','1','-A','Mozilla/5.0','-o',tmp,u], check=True)
            size=os.path.getsize(tmp)
            if size>50000:
                os.replace(tmp,path)
                print('SAVED', fn, size, flush=True)
                break
            print('TOO_SMALL', fn, size, flush=True)
        except Exception as e:
            print('ERR', fn, repr(e), flush=True)
            try:
                if os.path.exists(tmp): os.remove(tmp)
            except Exception: pass
    else:
        print('FAIL', fn, flush=True)
print('DONE_FAST', flush=True)
