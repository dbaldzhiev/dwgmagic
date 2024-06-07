import config as cfg    
import os
def accVersion():
        for key in cfg.accpathv:
            if os.path.exists(cfg.accpathv[key]):
                return cfg.accpathv[key]