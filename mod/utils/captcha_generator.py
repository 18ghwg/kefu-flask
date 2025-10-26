"""
拼图验证码生成器
"""
from PIL import Image, ImageDraw, ImageFilter
import random
import io
import base64
import os


class PuzzleCaptchaGenerator:
    """拼图验证码生成器"""
    
    def __init__(self, width=300, height=150):
        self.width = width
        self.height = height
        self.puzzle_size = 50  # 拼图块大小
        self.puzzle_offset = 5  # 拼图凸起偏移
        
    def generate(self, background_image_path=None):
        """
        生成拼图验证码
        
        Returns:
            dict: {
                'background': base64编码的背景图（带缺口）,
                'puzzle': base64编码的拼图块,
                'x': 拼图块正确的X坐标,
                'y': 拼图块的Y坐标
            }
        """
        # 1. 加载或生成背景图
        if background_image_path and os.path.exists(background_image_path):
            bg_img = Image.open(background_image_path).convert('RGB')
            bg_img = bg_img.resize((self.width, self.height))
        else:
            # 使用随机颜色生成背景图
            bg_img = self._generate_random_background()
        
        # 2. 随机生成拼图位置
        # X坐标：让拼图块可以在整个滑动范围内（0 到 width-puzzle_size）
        # 为了避免太靠边缘，稍微留出一点边距
        min_x = 10
        max_x = self.width - self.puzzle_size - 10  # 300 - 50 - 10 = 240
        puzzle_x = random.randint(min_x, max_x)
        
        # Y坐标：垂直方向留出边距
        puzzle_y = random.randint(10, self.height - self.puzzle_size - 10)
        
        # 3. 创建拼图形状蒙版
        puzzle_mask = self._create_puzzle_mask()
        
        # 4. 提取拼图块
        puzzle_piece = bg_img.crop((
            puzzle_x,
            puzzle_y,
            puzzle_x + self.puzzle_size,
            puzzle_y + self.puzzle_size
        ))
        
        # 应用拼图形状蒙版
        puzzle_piece_with_alpha = Image.new('RGBA', (self.puzzle_size, self.puzzle_size), (255, 255, 255, 0))
        puzzle_piece_with_alpha.paste(puzzle_piece, (0, 0))
        puzzle_piece_with_alpha.putalpha(puzzle_mask)
        
        # 添加边框和阴影效果
        puzzle_piece_with_alpha = self._add_puzzle_border(puzzle_piece_with_alpha, puzzle_mask)
        
        # 5. 在背景图上创建缺口
        bg_img_with_hole = bg_img.copy()
        self._create_hole(bg_img_with_hole, puzzle_x, puzzle_y, puzzle_mask)
        
        # 6. 转换为base64
        background_base64 = self._image_to_base64(bg_img_with_hole)
        puzzle_base64 = self._image_to_base64(puzzle_piece_with_alpha, format='PNG')
        
        return {
            'background': background_base64,
            'puzzle': puzzle_base64,
            'x': puzzle_x,
            'y': puzzle_y
        }
    
    def _generate_random_background(self):
        """生成随机背景图"""
        # 创建渐变背景
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)
        
        # 随机选择颜色方案
        color_schemes = [
            [(67, 97, 238), (99, 102, 241)],  # 蓝紫
            [(16, 185, 129), (5, 150, 105)],  # 绿色
            [(244, 63, 94), (225, 29, 72)],   # 粉红
            [(251, 146, 60), (249, 115, 22)], # 橙色
            [(168, 85, 247), (147, 51, 234)], # 紫色
        ]
        colors = random.choice(color_schemes)
        
        # 绘制渐变
        for i in range(self.height):
            ratio = i / self.height
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
            draw.line([(0, i), (self.width, i)], fill=(r, g, b))
        
        # 添加一些随机圆形装饰
        for _ in range(random.randint(5, 10)):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            radius = random.randint(10, 30)
            alpha = random.randint(20, 60)
            overlay = Image.new('RGBA', (self.width, self.height), (255, 255, 255, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=(255, 255, 255, alpha)
            )
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        
        return img
    
    def _create_puzzle_mask(self):
        """创建拼图形状蒙版（带凸起和凹陷）"""
        mask = Image.new('L', (self.puzzle_size, self.puzzle_size), 0)
        draw = ImageDraw.Draw(mask)
        
        # 基础矩形
        offset = self.puzzle_offset
        
        # 创建拼图轮廓路径
        path = []
        
        # 上边 - 带凸起
        path.append((0, offset))
        path.append((self.puzzle_size // 2 - offset, offset))
        # 上凸起（半圆）
        for i in range(0, 180, 10):
            angle = i * 3.14159 / 180
            x = self.puzzle_size // 2 + offset * 2 * (0.5 - 0.5 * (1 + abs(i - 90) / 90))
            y = offset - offset * abs((i - 90) / 90)
            path.append((x, y))
        path.append((self.puzzle_size // 2 + offset, offset))
        path.append((self.puzzle_size, offset))
        
        # 右边 - 带凹陷
        path.append((self.puzzle_size - offset, self.puzzle_size // 2 - offset))
        # 右凹陷（半圆）
        for i in range(90, 270, 10):
            angle = i * 3.14159 / 180
            x = self.puzzle_size - offset + offset * abs((i - 180) / 90)
            y = self.puzzle_size // 2 + offset * 2 * (0.5 - 0.5 * (1 + abs(i - 180) / 90))
            path.append((x, y))
        path.append((self.puzzle_size - offset, self.puzzle_size // 2 + offset))
        path.append((self.puzzle_size - offset, self.puzzle_size))
        
        # 下边
        path.append((0, self.puzzle_size - offset))
        
        # 左边
        path.append((offset, 0))
        
        # 填充拼图形状
        draw.polygon(path, fill=255)
        
        # 简化：直接画一个带凸起的形状
        draw = ImageDraw.Draw(mask)
        
        # 主体矩形
        draw.rectangle([5, 5, self.puzzle_size - 5, self.puzzle_size - 5], fill=255)
        
        # 上方凸起
        draw.ellipse([
            self.puzzle_size // 2 - 8,
            -8,
            self.puzzle_size // 2 + 8,
            12
        ], fill=255)
        
        # 右侧凹陷（用黑色圆遮挡）
        draw.ellipse([
            self.puzzle_size - 12,
            self.puzzle_size // 2 - 8,
            self.puzzle_size + 8,
            self.puzzle_size // 2 + 8
        ], fill=0)
        
        # 应用模糊使边缘更平滑
        mask = mask.filter(ImageFilter.SMOOTH)
        
        return mask
    
    def _add_puzzle_border(self, puzzle_img, mask):
        """为拼图块添加边框"""
        # 创建边框
        border = Image.new('RGBA', puzzle_img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(border)
        
        # 找到蒙版边缘并绘制白色边框
        pixels = mask.load()
        for x in range(1, self.puzzle_size - 1):
            for y in range(1, self.puzzle_size - 1):
                if pixels[x, y] > 128:
                    # 检查周围是否有透明像素
                    if (pixels[x-1, y] < 128 or pixels[x+1, y] < 128 or
                        pixels[x, y-1] < 128 or pixels[x, y+1] < 128):
                        draw.point((x, y), fill=(255, 255, 255, 200))
        
        # 合并边框和拼图
        result = Image.alpha_composite(puzzle_img, border)
        
        return result
    
    def _create_hole(self, bg_img, x, y, mask):
        """在背景图上创建缺口"""
        # 创建阴影效果
        shadow = Image.new('RGBA', bg_img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        
        # 在缺口位置绘制半透明黑色
        for py in range(self.puzzle_size):
            for px in range(self.puzzle_size):
                if mask.getpixel((px, py)) > 128:
                    img_x = x + px
                    img_y = y + py
                    if 0 <= img_x < self.width and 0 <= img_y < self.height:
                        # 获取原始像素并变暗
                        original_pixel = bg_img.getpixel((img_x, img_y))
                        darkened = tuple(int(c * 0.6) for c in original_pixel)
                        bg_img.putpixel((img_x, img_y), darkened)
        
        # 绘制边框
        pixels = mask.load()
        for px in range(1, self.puzzle_size - 1):
            for py in range(1, self.puzzle_size - 1):
                if pixels[px, py] > 128:
                    if (pixels[px-1, py] < 128 or pixels[px+1, py] < 128 or
                        pixels[px, py-1] < 128 or pixels[px, py+1] < 128):
                        img_x = x + px
                        img_y = y + py
                        if 0 <= img_x < self.width and 0 <= img_y < self.height:
                            bg_img.putpixel((img_x, img_y), (255, 255, 255))
    
    def _image_to_base64(self, img, format='JPEG'):
        """将图片转换为base64"""
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        if format == 'PNG':
            return f'data:image/png;base64,{img_base64}'
        else:
            return f'data:image/jpeg;base64,{img_base64}'
