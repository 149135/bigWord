import cv2
import numpy as np
import os
from PIL import Image

# 确保保存目录存在
def ensure_save_dirs():
    dirs = ['save/debug', 'save/results']
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                print(f"创建目录失败 {dir_path}: {e}")

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print("PaddleOCR未安装，车牌识别功能将不可用")

class PlateOCRPaddle:
    """基于PaddleOCR的车牌识别类"""
    
    def __init__(self):
        self.ocr = None
        self.initialized = False
        self.debug_mode = True
        
        ensure_save_dirs()
        
        if not PADDLEOCR_AVAILABLE:
            print("❌ PaddleOCR库未安装")
            return
            
        try:
            print("🔄 正在初始化PaddleOCR...")
            # 初始化 PaddleOCR (启用角度分类)
            # 注意：PaddlePaddle 在 Python 3.13 上可能存在兼容性问题
            self.ocr = PaddleOCR(use_angle_cls=False, lang='ch')
            self.initialized = True
            print("✅ PaddleOCR识别器初始化成功")
        except Exception as e:
            print(f"❌ PaddleOCR初始化失败: {e}")
            if "libpaddle" in str(e) or "partially initialized" in str(e):
                 print("💡 提示: 这可能是因为 Python 版本与 PaddlePaddle 不兼容 (推荐 Python 3.8-3.10)")
            # import traceback
            # traceback.print_exc()
            self.initialized = False

    def preprocess_plate_image(self, plate_img):
        """图像预处理"""
        if isinstance(plate_img, Image.Image):
            plate_img = np.array(plate_img)
        
        if len(plate_img.shape) == 2:
            plate_img = cv2.cvtColor(plate_img, cv2.COLOR_GRAY2BGR)
        
        # 保存调试图像
        if self.debug_mode:
            cv2.imwrite('save/debug/current_plate_processed.jpg', plate_img)
        
        return plate_img
        
    def extract_plate_number(self, plate_img, retry_reinit=False):
        """
        使用PaddleOCR识别车牌号码
        """
        # Lazy retry or force re-initialization
        if not self.initialized or retry_reinit:
            if retry_reinit:
                print("🔄 强制重新初始化OCR...")
            else:
                print("⚠️ OCR未初始化，尝试重新初始化...")
            try:
                self.ocr = PaddleOCR(use_angle_cls=False, lang='ch')
                self.initialized = True
                print("✅ PaddleOCR初始化成功")
            except Exception as e:
                print(f"❌ PaddleOCR初始化失败: {e}")
                return ""

        if not self.initialized:
            print("⚠️ OCR未初始化，返回空")
            return ""

        try:
            # Check if image is empty before preprocessing
            if plate_img is None or plate_img.size == 0:
                print("⚠️ 输入OCR的图像为空")
                return ""

            # 预处理
            processed_img = self.preprocess_plate_image(plate_img)
            
            print("🔍 开始PaddleOCR识别...")
            # 运行OCR
            result = self.ocr.ocr(processed_img, cls=False)
            
            if not result or result[0] is None:
                print("⚠️ 未检测到文字")
                return ""

            
            # 提取结果: result = [[[[x1,y1]..], ("text", conf)], ...]
            # 我们只需要置信度最高的或者合并所有文本，通常车牌是一个短文本
            
            detected_texts = []
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                print(f"  - 识别片段: '{text}' (置信度: {confidence:.2f})")
                detected_texts.append(text)
            
            # 简单的拼接或选择最像车牌的
            # 车牌通常是单个文本块，但有时会被分成两行（如双层车牌）
            # 这里简单返回第一个识别到的长文本，或者拼接
            
            full_text = "".join(detected_texts)
            
            # 简单的清理（去除非法字符）
            import re
            # 保留汉字、字母、数字
            clean_text = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', full_text)
            
            print(f"🎯 最终识别结果: '{clean_text}'")
            return clean_text

        except Exception as e:
            print(f"❌ 车牌识别异常: {e}")
            return ""

    def extract_plate_from_image(self, image, box_coords):
        """从大图中提取车牌并识别"""
        try:
            print(f"📌 处理车牌坐标: {box_coords}")
            
            if len(box_coords) == 4:
                x1, y1, x2, y2 = map(int, box_coords)
            else:
                 # Handle potentially other formats or fail
                 x1, y1, x2, y2 = map(int, box_coords[:4])

            # 边界检查和扩展区域（防止裁剪过小）
            h, w = image.shape[:2]
            
            # 计算当前区域大小
            box_width = x2 - x1
            box_height = y2 - y1
            
            # 如果区域太小，扩展边界（增加10%的边距）
            if box_width < 100 or box_height < 30:
                expand_x = int(box_width * 0.1)
                expand_y = int(box_height * 0.1)
                x1 = max(0, x1 - expand_x)
                y1 = max(0, y1 - expand_y)
                x2 = min(w, x2 + expand_x)
                y2 = min(h, y2 + expand_y)
                print(f"🔧 扩展识别区域: [{x1}, {y1}, {x2}, {y2}]")
            
            # 最终边界检查
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                print("⚠️ 无效的裁剪区域")
                return ""

            plate_region = image[y1:y2, x1:x2]
            
            # 验证裁剪后的图像
            if plate_region.size == 0:
                print("⚠️ 裁剪后图像为空")
                return ""
            
            if self.debug_mode:
                cv2.imwrite('save/debug/extracted_plate.jpg', plate_region)
            
            # Try normal recognition first
            result = self.extract_plate_number(plate_region, retry_reinit=False)
            
            # If failed with "could not execute" error, try with OCR re-initialization
            if not result or len(result) == 0:
                print("⚠️ 首次识别失败，尝试重新初始化OCR后再试...")
                result = self.extract_plate_number(plate_region, retry_reinit=True)
                
            return result
            
        except Exception as e:
            print(f"❌ 车牌提取异常: {e}")
            return ""

# 全局实例
plate_ocr_paddle = PlateOCRPaddle()

def get_plate_number_paddle(image, box_coords):
    return plate_ocr_paddle.extract_plate_from_image(image, box_coords)
