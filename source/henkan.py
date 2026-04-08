
import os
import re
from PIL import Image
import numpy as np

def main():
    # 定数
    bai = 13913
    sc  = 519  # HSP の sc=569 に対応

    # 作業ディレクトリ内のファイル名から “screenA_数字.bmp” を探して数字を集める
    #pattern = re.compile(r"screenA_(\d+)\.bmp$")
    pattern = re.compile(r"screenA_(.+)\.bmp$")
    nums = []
    for fname in os.listdir("."):
        m = pattern.match(fname)
        if m:
            nums.append(m.group(1))
    nums = sorted(set(nums))
    if not nums:
        print("▶ screenA_*.bmp が見つかりませんでした。")
        return

    for num in nums:
        # ファイル名を組み立て
        fnA = f"screenA_{num}.bmp"
        fnB = f"screenB_{num}.bmp"
        fnC = f"screenC_{num}.bmp"
        fnD = f"screenD_{num}.bmp"
        # ４つ揃っているかチェック
        if not all(os.path.exists(fn) for fn in (fnA, fnB, fnC, fnD)):
            print(f"▶ スキップ：{num} の A～D のいずれかが欠如しています")
            continue

        # 画像読み込み→float32 配列に変換
        arrA = np.array(Image.open(fnA), dtype=np.float32)
        arrB = np.array(Image.open(fnB), dtype=np.float32)
        arrC = np.array(Image.open(fnC), dtype=np.float32)
        arrD = np.array(Image.open(fnD), dtype=np.float32)

        # 再構築
        reconstructed = (
            arrA * 65536 * bai +
            arrB *   256 * bai +
            arrC *     1 * bai +
            arrD * (bai / 256.0)
        ) / sc

        # clamp & uint8 化
        reconstructed = np.clip(reconstructed, 0, 255).astype(np.uint8)

        # 保存
        out_name = f"out_{num}.png"
        Image.fromarray(reconstructed).save(out_name)
        print(f"✔ 出力：{out_name}")
        
        """
        # 元画像を削除
        for fn in (fnA, fnB, fnC, fnD):
            try:
                os.remove(fn)
                print(f"🗑 削除：{fn}")
            except OSError as e:
                print(f"⚠ 削除失敗：{fn} ({e})")
        """

if __name__ == "__main__":
    main()
