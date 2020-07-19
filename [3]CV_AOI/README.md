# AOI

	01: 基礎模型
	02: 改進 dataflow
	03: 使用 EfficientNet-B5
	04: v1 改用 flow_from_dataframe 載入資料
		v2 使用 data augmentation (rotation range、
								   horizontal flip、
								   vertival flip、
								   width shift range、
								   height shift range、
								   shear range、
								   zoom range)
		v3 使用 RectifiedAdam + Lookahead，並取消 data augmentation
		v4 使用 Adam + Lookahead，並取消 data augmentation