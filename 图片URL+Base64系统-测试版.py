import os
import math
from flask import Flask, send_from_directory, render_template_string, jsonify, request
from werkzeug.utils import secure_filename
from datetime import datetime
import base64

app = Flask(__name__)

# 配置参数
IMAGE_FOLDER = r'D:\任务分配\图像URL'
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5004
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# 关键优化：分页配置
IMAGES_PER_PAGE = 20  # 每页只显示20张图片
MAX_PREVIEW_SIZE = 300  # 预览图最大宽度

# 全局状态变量
server_start_time = None
processed_images = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_uptime():
    if server_start_time:
        delta = datetime.now() - server_start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}小时{minutes}分钟"
    return "未知"

def scan_image_folder():
    """扫描图片目录，不预加载base64以提高性能"""
    global processed_images
    base_url = f"http://{SERVER_HOST}:{SERVER_PORT}/images/"
    processed_images = []
    
    if not os.path.exists(IMAGE_FOLDER):
        return
    
    for filename in sorted(os.listdir(IMAGE_FOLDER)):
        if allowed_file(filename):
            filepath = os.path.join(IMAGE_FOLDER, filename)
            if os.path.exists(filepath):
                processed_images.append({
                    'filename': filename,
                    'url': base_url + filename,
                    'filepath': filepath
                })

# 优化后的HTML模板（分页版本）
HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>图片URL服务器管理中心 - 优化版</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        .header { 
            text-align: center; 
            color: white; 
            margin-bottom: 30px; 
            background: rgba(0,0,0,0.1);
            padding: 20px;
            border-radius: 15px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header .warning {
            background: #ff6b6b;
            color: white;
            padding: 10px;
            border-radius: 10px;
            margin-top: 15px;
            font-weight: bold;
        }
        
        .card { 
            background: white; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            margin-bottom: 20px; 
            overflow: hidden; 
        }
        .card-header { 
            background: linear-gradient(90deg, #4CAF50, #45a049); 
            color: white; 
            padding: 20px; 
            font-size: 1.2em; 
            font-weight: bold; 
        }
        .card-body { padding: 20px; }
        
        /* 分页样式 */
        .pagination-container {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }
        .pagination {
            display: inline-flex;
            gap: 5px;
            align-items: center;
            flex-wrap: wrap;
        }
        .pagination a, .pagination span {
            padding: 10px 15px;
            border: 1px solid #ddd;
            text-decoration: none;
            border-radius: 8px;
            color: #333;
            font-weight: 500;
            transition: all 0.3s;
        }
        .pagination a:hover {
            background: #4CAF50;
            color: white;
            transform: translateY(-2px);
        }
        .pagination .current {
            background: #4CAF50;
            color: white;
            font-weight: bold;
        }
        .page-info {
            margin: 15px 0;
            color: #666;
            font-size: 1.1em;
        }
        
        /* 状态网格 */
        .status-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin: 20px 0; 
        }
        .status-item { 
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
            border-left: 5px solid #4CAF50; 
            transition: transform 0.3s;
        }
        .status-item:hover { transform: translateY(-3px); }
        .status-item h3 { color: #4CAF50; font-size: 2em; margin-bottom: 10px; }
        
        /* 图片网格优化 */
        .image-gallery { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); 
            gap: 20px;
            margin: 20px 0;
        }
        .image-item { 
            background: white; 
            border-radius: 12px; 
            overflow: hidden; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1); 
            transition: transform 0.3s, box-shadow 0.3s; 
        }
        .image-item:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        .image-preview { 
            width: 100%; 
            height: 200px; 
            object-fit: cover; 
            background: #f8f9fa;
            loading: lazy; /* 原生懒加载 */
        }
        .image-info { 
            padding: 15px; 
            background: #f8f9fa;
        }
        .image-info h4 {
            color: #333;
            margin-bottom: 5px;
            font-size: 0.9em;
            word-break: break-all;
        }
        .image-actions { 
            padding: 15px; 
            display: flex; 
            gap: 8px; 
            flex-wrap: wrap; 
        }
        
        .btn { 
            padding: 8px 12px; 
            border: none; 
            border-radius: 20px; 
            cursor: pointer; 
            font-size: 12px; 
            text-decoration: none; 
            display: inline-block; 
            transition: all 0.3s;
            font-weight: 500;
        }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-danger { background: #f44336; color: white; }
        .btn:hover { transform: translateY(-2px); }
        .btn:disabled { 
            opacity: 0.6; 
            cursor: not-allowed; 
            transform: none; 
        }
        
        .upload-area { 
            border: 3px dashed #ddd; 
            border-radius: 15px; 
            padding: 40px; 
            text-align: center; 
            margin: 20px 0; 
            cursor: pointer; 
            transition: all 0.3s;
        }
        .upload-area:hover { 
            border-color: #4CAF50; 
            background-color: #f0fff0; 
        }
        .upload-area input[type="file"] { display: none; }
        
        .alert { 
            padding: 15px; 
            border-radius: 10px; 
            margin: 20px 0; 
            font-weight: 500;
        }
        .alert-success { background: #d4edda; color: #155724; border-left: 5px solid #28a745; }
        .alert-error { background: #f8d7da; color: #721c24; border-left: 5px solid #dc3545; }
        .alert-info { background: #d1ecf1; color: #0c5460; border-left: 5px solid #17a2b8; }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-state h3 { margin-bottom: 15px; font-size: 1.5em; }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header h1 { font-size: 2em; }
            .image-gallery { grid-template-columns: 1fr; }
            .pagination { justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>图片URL服务器管理中心</h1>
            <p>性能优化版 - 分页加载避免浏览器崩溃</p>
            {% if total_images > 100 %}
            <div class="warning">
                检测到大量图片 ({{ total_images }}张)，已启用分页模式保护系统性能
            </div>
            {% endif %}
        </div>

        <!-- 服务器状态 -->
        <div class="card">
            <div class="card-header">服务器状态总览</div>
            <div class="card-body">
                <div class="status-grid">
                    <div class="status-item">
                        <h3>{{ uptime }}</h3>
                        <p>运行时长</p>
                    </div>
                    <div class="status-item">
                        <h3>{{ total_images }}</h3>
                        <p>图片总数</p>
                    </div>
                    <div class="status-item">
                        <h3>{{ current_page }}/{{ total_pages }}</h3>
                        <p>当前页/总页数</p>
                    </div>
                    <div class="status-item">
                        <h3>{{ images_per_page }}</h3>
                        <p>每页显示数量</p>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 20px;">
                    <button onclick="window.location.reload()" class="btn btn-secondary">刷新页面</button>
                    <button onclick="clearAllImages()" class="btn btn-danger">清空所有图片</button>
                </div>
            </div>
        </div>

        <!-- 文件上传 -->
        <div class="card">
            <div class="card-header">文件上传</div>
            <div class="card-body">
                <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
                    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                        <input type="file" id="fileInput" name="files" multiple accept="image/*">
                        <h3>点击选择图片或拖拽到此处</h3>
                        <p>支持多文件上传 | 支持格式: PNG, JPG, JPEG, GIF, BMP, WEBP</p>
                        <p style="color: #666; margin-top: 10px;">
                            当前每页显示 {{ images_per_page }} 张图片，大量图片将自动分页
                        </p>
                    </div>
                    <div style="text-align: center; margin: 20px 0;">
                        <button type="submit" class="btn btn-primary">开始上传</button>
                        <button type="button" onclick="clearFileSelection()" class="btn btn-secondary">清除选择</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- 分页导航 -->
        {% if total_pages > 1 %}
        <div class="pagination-container">
            <div class="page-info">
                显示第 {{ start_index }}-{{ end_index }} 项，共 {{ total_images }} 项
            </div>
            <div class="pagination">
                {% if current_page > 1 %}
                    <a href="/?page=1" title="首页">&laquo;&laquo; 首页</a>
                    <a href="/?page={{ current_page - 1 }}" title="上一页">&laquo; 上一页</a>
                {% endif %}
                
                {% for page_num in page_numbers %}
                    {% if page_num == current_page %}
                        <span class="current">{{ page_num }}</span>
                    {% else %}
                        <a href="/?page={{ page_num }}">{{ page_num }}</a>
                    {% endif %}
                {% endfor %}
                
                {% if current_page < total_pages %}
                    <a href="/?page={{ current_page + 1 }}" title="下一页">下一页 &raquo;</a>
                    <a href="/?page={{ total_pages }}" title="末页">末页 &raquo;&raquo;</a>
                {% endif %}
            </div>
            <div style="margin-top: 15px;">
                <input type="number" id="jumpPage" placeholder="页码" min="1" max="{{ total_pages }}" style="padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
                <button onclick="jumpToPage()" class="btn btn-secondary">跳转</button>
            </div>
        </div>
        {% endif %}

        <!-- 图片管理 -->
        <div class="card">
            <div class="card-header">
                图片管理 - 第{{ current_page }}页 
                {% if page_images %}({{ page_images|length }}张){% endif %}
            </div>
            <div class="card-body">
                {% if page_images %}
                <div class="image-gallery">
                    {% for img in page_images %}
                    <div class="image-item">
                        <img src="{{ img.url }}" 
                             alt="{{ img.filename }}" 
                             class="image-preview" 
                             loading="lazy"
                             onerror="this.src='data:image/svg+xml,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"300\" height=\"200\"><rect width=\"100%\" height=\"100%\" fill=\"%23f8f9fa\"/><text x=\"50%\" y=\"50%\" fill=\"%23666\" text-anchor=\"middle\" dy=\".3em\">加载失败</text></svg>'">
                        <div class="image-info">
                            <h4>{{ img.filename }}</h4>
                        </div>
                        <div class="image-actions">
                            <a href="{{ img.url }}" target="_blank" class="btn btn-primary">预览</a>
                            <button onclick="copyUrl('{{ img.url }}')" class="btn btn-secondary">复制URL</button>
                            <button onclick="generateBase64('{{ img.filename }}', {{ loop.index0 }})" 
                                    class="btn btn-secondary" 
                                    id="base64_btn_{{ loop.index0 }}">生成Base64</button>
                            <button onclick="deleteImage('{{ img.filename }}')" class="btn btn-danger">删除</button>
                        </div>
                        <div id="base64_result_{{ loop.index0 }}" style="display: none; padding: 15px; background: #f8f9fa;">
                            <small>Base64编码:</small>
                            <textarea id="base64_content_{{ loop.index0 }}" readonly style="width: 100%; height: 60px; font-size: 10px; font-family: monospace;"></textarea>
                            <button onclick="copyBase64({{ loop.index0 }})" class="btn btn-secondary" style="margin-top: 5px;">复制Base64</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="empty-state">
                    <h3>这一页暂无图片</h3>
                    <p>请上传图片或查看其他页面</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        // 上传表单处理
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('fileInput');
            if (fileInput.files.length === 0) {
                showAlert('error', '请先选择文件！');
                return;
            }
            
            const formData = new FormData();
            for (let i = 0; i < fileInput.files.length; i++) {
                formData.append('files', fileInput.files[i]);
            }
            
            showAlert('info', '正在上传文件...');
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('success', `成功上传 ${data.uploaded_count} 个文件！页面将刷新...`);
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    showAlert('error', '上传失败: ' + data.message);
                }
            })
            .catch(error => {
                showAlert('error', '上传失败: ' + error.message);
            });
        });

        // 清除文件选择
        function clearFileSelection() {
            document.getElementById('fileInput').value = '';
        }

        // 复制URL
        function copyUrl(url) {
            navigator.clipboard.writeText(url).then(() => {
                showAlert('success', 'URL已复制到剪贴板！');
            }).catch(err => {
                showAlert('error', '复制失败，请手动复制');
            });
        }

        // 生成Base64
        function generateBase64(filename, index) {
            const button = document.getElementById(`base64_btn_${index}`);
            const originalText = button.textContent;
            
            button.textContent = '生成中...';
            button.disabled = true;
            
            fetch(`/generate_base64/${encodeURIComponent(filename)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const resultDiv = document.getElementById(`base64_result_${index}`);
                    const contentArea = document.getElementById(`base64_content_${index}`);
                    contentArea.value = data.base64;
                    resultDiv.style.display = 'block';
                    button.textContent = '重新生成';
                    showAlert('success', 'Base64生成完成！');
                } else {
                    showAlert('error', 'Base64生成失败: ' + data.message);
                    button.textContent = originalText;
                }
                button.disabled = false;
            })
            .catch(error => {
                showAlert('error', '请求失败: ' + error.message);
                button.textContent = originalText;
                button.disabled = false;
            });
        }

        // 复制Base64
        function copyBase64(index) {
            const contentArea = document.getElementById(`base64_content_${index}`);
            contentArea.select();
            navigator.clipboard.writeText(contentArea.value).then(() => {
                showAlert('success', 'Base64已复制到剪贴板！');
            }).catch(err => {
                showAlert('error', '复制失败，请手动复制');
            });
        }

        // 删除图片
        function deleteImage(filename) {
            if (confirm(`确定要删除 "${filename}" 吗？此操作不可恢复！`)) {
                fetch(`/delete/${encodeURIComponent(filename)}`, {method: 'DELETE'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('success', '文件删除成功！页面将刷新...');
                        setTimeout(() => window.location.reload(), 1500);
                    } else {
                        showAlert('error', '删除失败: ' + data.message);
                    }
                })
                .catch(error => {
                    showAlert('error', '删除失败: ' + error.message);
                });
            }
        }

        // 清空所有图片
        function clearAllImages() {
            if (confirm('确定要清空所有图片吗？此操作不可恢复！')) {
                fetch('/clear_all', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('success', '所有文件已清空！页面将刷新...');
                        setTimeout(() => window.location.reload(), 1500);
                    } else {
                        showAlert('error', '清空失败: ' + data.message);
                    }
                })
                .catch(error => {
                    showAlert('error', '清空失败: ' + error.message);
                });
            }
        }

        // 页面跳转
        function jumpToPage() {
            const pageInput = document.getElementById('jumpPage');
            const pageNum = parseInt(pageInput.value);
            if (pageNum && pageNum >= 1 && pageNum <= {{ total_pages }}) {
                window.location.href = `/?page=${pageNum}`;
            } else {
                showAlert('error', '请输入有效的页码 (1-{{ total_pages }})');
            }
        }

        // 显示提示
        function showAlert(type, message) {
            // 移除已存在的提示
            const existingAlert = document.querySelector('.alert');
            if (existingAlert) {
                existingAlert.remove();
            }
            
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.textContent = message;
            
            // 添加关闭按钮
            const closeBtn = document.createElement('span');
            closeBtn.style.cssText = 'float: right; cursor: pointer; font-weight: bold;';
            closeBtn.textContent = '×';
            closeBtn.onclick = () => alertDiv.remove();
            alertDiv.appendChild(closeBtn);
            
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.card'));
            
            // 自动移除
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }

        // 拖拽上传
        const uploadArea = document.querySelector('.upload-area');
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.style.borderColor = '#4CAF50';
                uploadArea.style.backgroundColor = '#f0fff0';
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.style.borderColor = '#ddd';
                uploadArea.style.backgroundColor = 'transparent';
            }, false);
        });
        
        uploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            document.getElementById('fileInput').files = files;
        }

        // 回车键跳转页面
        document.getElementById('jumpPage').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                jumpToPage();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """主页面 - 分页版本"""
    scan_image_folder()
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    page = max(1, page)
    
    # 计算分页
    total_images = len(processed_images)
    total_pages = math.ceil(total_images / IMAGES_PER_PAGE) if total_images > 0 else 1
    page = min(page, total_pages)
    
    start_index = (page - 1) * IMAGES_PER_PAGE
    end_index = start_index + IMAGES_PER_PAGE
    page_images = processed_images[start_index:end_index]
    
    # 生成页码列表（智能分页）
    page_numbers = []
    if total_pages <= 10:
        page_numbers = list(range(1, total_pages + 1))
    else:
        if page <= 6:
            page_numbers = list(range(1, 11))
        elif page >= total_pages - 5:
            page_numbers = list(range(total_pages - 9, total_pages + 1))
        else:
            page_numbers = list(range(page - 5, page + 6))
    
    return render_template_string(
        HOME_TEMPLATE,
        page_images=page_images,
        total_images=total_images,
        current_page=page,
        total_pages=total_pages,
        images_per_page=IMAGES_PER_PAGE,
        start_index=start_index + 1,
        end_index=min(end_index, total_images),
        page_numbers=page_numbers,
        uptime=calculate_uptime()
    )

@app.route('/images/<filename>')
def serve_image(filename):
    """提供图片文件访问"""
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/generate_base64/<filename>')
def generate_base64_single(filename):
    """为单个图片生成Base64"""
    try:
        filepath = os.path.join(IMAGE_FOLDER, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as img_file:
                img_data = img_file.read()
                base64_str = base64.b64encode(img_data).decode('utf-8')
                
                # 获取MIME类型
                ext = os.path.splitext(filename)[1].lower()
                mime_type = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg', 
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp'
                }.get(ext, 'image/jpeg')
                
                full_base64 = f"data:{mime_type};base64,{base64_str}"
                return jsonify({'success': True, 'base64': full_base64})
        else:
            return jsonify({'success': False, 'message': '文件不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/upload', methods=['POST'])
def upload_files():
    """上传文件"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'message': '未找到文件'})
        
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': '未选择文件'})
        
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        
        uploaded_count = 0
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    if filename:
                        filepath = os.path.join(IMAGE_FOLDER, filename)
                        file.save(filepath)
                        uploaded_count += 1
                except Exception as e:
                    print(f"保存文件失败: {e}")
        
        return jsonify({
            'success': True, 
            'uploaded_count': uploaded_count,
            'message': f'成功上传 {uploaded_count} 个文件'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """删除指定文件"""
    try:
        filepath = os.path.join(IMAGE_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'success': True, 'message': f'文件 {filename} 删除成功'})
        else:
            return jsonify({'success': False, 'message': '文件不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/clear_all', methods=['POST'])
def clear_all():
    """清空所有文件"""
    try:
        deleted_count = 0
        if os.path.exists(IMAGE_FOLDER):
            for filename in os.listdir(IMAGE_FOLDER):
                if allowed_file(filename):
                    filepath = os.path.join(IMAGE_FOLDER, filename)
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception as e:
                        print(f"删除文件失败 {filename}: {e}")
        
        return jsonify({
            'success': True, 
            'message': f'成功删除 {deleted_count} 个文件'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    print("\n\n收到停止信号，正在关闭服务器...")
    print("服务器已安全关闭")
    sys.exit(0)

def main():
    """主函数"""
    global server_start_time
    server_start_time = datetime.now()
    
    # 注册信号处理器
    import signal
    import sys
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("图片URL服务器 - 性能优化版")
    print("=" * 60)
    print(f"服务器地址: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"图片目录: {IMAGE_FOLDER}")
    print(f"每页显示: {IMAGES_PER_PAGE} 张图片")
    print("=" * 60)
    print("主要优化:")
    print("- 分页加载，避免浏览器崩溃")
    print("- 懒加载图片预览")
    print("- 按需生成Base64编码")
    print("- 智能分页导航")
    print("- 响应式设计")
    print("=" * 60)
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        # 确保图片目录存在
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        
        # 初始扫描
        scan_image_folder()
        print(f"初始扫描完成，发现 {len(processed_images)} 个图片文件")
        
        if len(processed_images) > 100:
            print(f"警告: 检测到大量图片 ({len(processed_images)}张)")
            print("已启用分页模式以保护系统性能")
        
        # 启动Flask应用
        app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        print("请检查端口是否被占用或权限设置")
    finally:
        print("服务器已关闭")

if __name__ == '__main__':
    main()
