## Introduction
FFTを使わずに直接回折を計算して光芒画像を生成するコード&exe  

## Input
画像サイズは256～2048。FFT使ってないので2べきじゃなくてもよい  
入力画像は黒い部分が遮蔽、白が光を透過。白い部分が多いほど計算時間が増える  
![input.png](https://github.com/user-attachments/assets/b1c7d72b-7b08-4088-b89d-c30a898ca4f8)  

## Output
完成イメージ  
![out.png](https://github.com/user-attachments/assets/ce02f1f2-4f23-4b31-98e6-3ae9e2e51674)


##やり方
### Step1
//Step1  
//直接法のほうが綺麗なことがわかったのでさらに綺麗さを追求&最適化  
//色は波長→RGBを等色関数で計算をする  
//これによって入力スペクトルにしたがっていろんな色の光芒が作れるように  
//double型,float型指定可能  
//画像サイズは256～2048。FFT使ってないので2べきじゃなくてもよい  
//入力画像は黒い部分が遮蔽、白が光を透過。白い部分が多いほど計算時間が増える  
//FFTの高速化は標本サイズの制限が出るので実装しない予定  
//出力は1ピクセルの1色あたりfloat=4byteの情報があるので4枚bmpに8bitずつ出力  
### Step2
4枚のbmpをpngに変換するだけ

### Step3
4枚のbmpを最終的にいい感じに1枚のpngに  

