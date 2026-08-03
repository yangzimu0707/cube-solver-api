# 预构建原语库缓存（pickle 到 cache/ 目录），避免 Render 首次请求时
# 构建库超过 60 秒请求限制导致 500/超时。
import os, pickle, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from centers import CenterLibrary
from edges import EdgeLibrary
from corners import CornerLibrary

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def build_and_save(name, lib):
    t0 = time.time()
    lib.build()
    path = os.path.join(CACHE_DIR, f"{name}.pkl")
    with open(path, "wb") as f:
        pickle.dump(lib, f, protocol=pickle.HIGHEST_PROTOCOL)
    size = os.path.getsize(path) / 1e6
    entries = sum(len(v) for v in lib._by_sorted.values())
    print(f"{name}: {size:.1f}MB, 构建 {time.time()-t0:.1f}s, 条目 {entries}")


if __name__ == "__main__":
    t_total = time.time()
    for n, prefix in [(4, "4"), (5, "5")]:
        build_and_save(f"center{prefix}", CenterLibrary(n))
        build_and_save(f"edge{prefix}", EdgeLibrary(n))
        build_and_save(f"corner{prefix}", CornerLibrary(n))
    print(f"总用时 {time.time()-t_total:.1f}s")
