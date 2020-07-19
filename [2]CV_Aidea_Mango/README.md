# AI CUP 2020｜愛文芒果影像辨識雙項競賽
# https://aidea-web.tw/

![image](https://github.com/oange6214/Projects/raw/master/01_Aidea_Mango/image/mango_01.png)

	v1   基礎模型建立
	v2   使用 Data augmentation
	v3   設計 Learning rate
	v4   EMA 找出最佳驗證機率
	v5   BN-Relu + GAP2d
	v6   圖片預處理由 0~1 改 -1~1、BN-Relu 去除
	  -1 資料集 + Cutout(以儲存成圖片)
	  -2 利用混淆矩陣，人工篩選圖片，將不佳的圖片去除。
	  -3 改用 GMP
	  -4 ImageDataGenerator 參數調整
	v7   改用 BN-Leaky-Relu
	v9   沿用 6-4，先訓練權重，再利用新權重二次訓練。


	predict    用於預測測試集，並將答案寫入。

	ensemble   利用先前訓練好的模型，進行 ensemble 用於增加準確率。


	minidataset-v1   使用小資料集進行測試
	minidataset-v2	 改用 BN-Relu + GAP
	minidataset-v3   改用 flow_from_directory、解析度 300
	minidataset-v4   dataset 重新調整

	Dataset-IncepResNetV2-effic-v1   資料集為 npz，嚐試使用 tf.data.Dataset 建立 資料流，使用 Inception-EfficientNetB7

	05_labelme 製作 UNet 訓練用 Mask
