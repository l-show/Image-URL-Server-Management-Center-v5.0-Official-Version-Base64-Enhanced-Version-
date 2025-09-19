import os
import csv
import json
from flask import Flask, send_from_directory, render_template_string, jsonify, request
from werkzeug.utils import secure_filename
import threading
import time
import signal
import sys
from datetime import datetime
import shutil
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB

# 配置参数
IMAGE_FOLDER = r'D:\任务分配\图像URL'
CSV_PATH = r'D:\任务分配\图片URL.csv'
CSV_BACKUP_PATH = r'D:\任务分配\图片URL_backup.csv'
STATUS_FILE = r'D:\任务分配\server_status.json'
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5004
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# 全局状态变量
server_start_time = None
processed_images = []

# 增强的HTML模板
HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>图片URL服务器管理中心</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; color: white; margin-bottom: 30px; position: relative; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header-links { position: absolute; top: 0; right: 0; display: flex; gap: 10px; }
        .header-link { background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; color: white; text-decoration: none; font-size: 0.9em; transition: all 0.3s; }
        .header-link:hover { background: rgba(255,255,255,0.3); transform: translateY(-2px); }
        .card { background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin-bottom: 20px; overflow: hidden; }
        .card-header { background: linear-gradient(90deg, #4CAF50, #45a049); color: white; padding: 20px; font-size: 1.2em; font-weight: bold; }
        .card-body { padding: 20px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .status-item { background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #4CAF50; }
        .upload-area { border: 3px dashed #ddd; border-radius: 10px; padding: 40px; text-align: center; margin: 20px 0; transition: all 0.3s; cursor: pointer; position: relative; }
        .upload-area:hover, .upload-area.dragover { border-color: #4CAF50; background-color: #f0fff0; }
        .upload-area.has-files { border-color: #2196F3; background-color: #e3f2fd; }
        .upload-area input[type="file"] { display: none; }
        .upload-content { transition: all 0.3s; }
        
        /* 文件列表滚动窗口样式 */
        .file-list-container { 
            max-height: 300px; 
            overflow-y: auto; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            margin-top: 15px;
            background: #fff;
        }
        .file-list { 
            padding: 10px;
        }
        .file-item { 
            background: #f8f9fa; 
            padding: 12px; 
            margin: 8px 0; 
            border-radius: 6px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            border-left: 3px solid #007bff;
            transition: all 0.2s;
        }
        .file-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .file-info {
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }
        .file-name {
            font-weight: 500;
            color: #333;
            margin-bottom: 2px;
        }
        .file-size {
            font-size: 0.85em;
            color: #666;
        }
        .remove-file { 
            background: #dc3545; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            padding: 6px 12px; 
            cursor: pointer; 
            font-size: 0.9em;
            transition: background 0.2s;
        }
        .remove-file:hover {
            background: #c82333;
        }
        
        /* 文件统计信息 */
        .files-summary {
            background: linear-gradient(90deg, #17a2b8, #138496);
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            text-align: center;
        }
        .summary-item h4 {
            font-size: 1.2em;
            margin-bottom: 5px;
        }
        .summary-item p {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .btn { padding: 12px 25px; border: none; border-radius: 25px; cursor: pointer; font-weight: bold; text-decoration: none; display: inline-block; transition: all 0.3s; }
        .btn-primary { background: linear-gradient(90deg, #4CAF50, #45a049); color: white; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .btn-primary:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .btn-danger { background: linear-gradient(90deg, #f44336, #d32f2f); color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        
        /* 图片管理滚动窗口 */
        .image-gallery-container {
            max-height: 600px;
            overflow-y: auto;
            border: 2px solid #eee;
            border-radius: 10px;
            padding: 15px;
            background: #fafafa;
        }
        .image-gallery { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); 
            gap: 20px;
        }
        .image-item { 
            background: white; 
            border-radius: 10px; 
            overflow: hidden; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1); 
            transition: transform 0.3s; 
        }
        .image-item:hover { transform: translateY(-5px); }
        .image-preview { 
            width: 100%; 
            height: 200px; 
            object-fit: cover; 
            background: #f8f9fa;
        }
        .image-error-placeholder {
            width: 100%; 
            height: 200px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            background: #f5f5f5; 
            color: #999;
            font-size: 14px;
        }
        .image-info { padding: 15px; }
        .image-actions { padding: 0 15px 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        .url-display { background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; word-break: break-all; margin: 10px 0; }
        .progress-bar { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #4CAF50, #45a049); transition: width 0.3s; border-radius: 10px; }
        .alert { padding: 15px; border-radius: 10px; margin: 20px 0; animation: slideIn 0.3s ease-out; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-info { background: #cce7ff; color: #004085; border: 1px solid #b3d7ff; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: white; margin: 5% auto; padding: 20px; width: 90%; max-width: 500px; border-radius: 15px; }
        .close { float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: red; }
        .refresh-timer { position: fixed; top: 20px; right: 20px; background: rgba(255,255,255,0.9); padding: 10px 15px; border-radius: 25px; z-index: 100; }
        
        /* 版权信息样式 */
        .footer {
            text-align: center;
            color: white;
            padding: 30px 20px;
            margin-top: 40px;
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        .footer h4 {
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .footer p {
            margin-bottom: 5px;
            opacity: 0.9;
        }
        .footer .developer-info {
            margin-top: 15px;
            font-size: 0.95em;
        }
        
        @keyframes slideIn { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
        
        /* 滚动条美化 */
        .file-list-container::-webkit-scrollbar,
        .image-gallery-container::-webkit-scrollbar {
            width: 8px;
        }
        .file-list-container::-webkit-scrollbar-track,
        .image-gallery-container::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        .file-list-container::-webkit-scrollbar-thumb,
        .image-gallery-container::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        .file-list-container::-webkit-scrollbar-thumb:hover,
        .image-gallery-container::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-links">
                <a href="/status" class="header-link" target="_blank">📊 状态API</a>
                <a href="javascript:void(0)" onclick="downloadCSV()" class="header-link">💾 下载CSV</a>
            </div>
            <h1>🖼️ 图片URL服务器管理中心</h1>
            <p>智能图片管理与URL生成系统 - 正式版</p>
        </div>

        <!-- 刷新倒计时 -->
        <div class="refresh-timer">
            <span id="refresh-countdown">30</span>秒后刷新
        </div>

        <!-- 服务器状态卡片 -->
        <div class="card">
            <div class="card-header">📊 服务器状态</div>
            <div class="card-body">
                <div class="status-grid">
                    <div class="status-item">
                        <h3>⏱️ {{ uptime }}</h3>
                        <p>运行时长</p>
                    </div>
                    <div class="status-item">
                        <h3>🖼️ {{ total_images }}</h3>
                        <p>图片总数</p>
                    </div>
                    <div class="status-item">
                        <h3>✅ {{ success_rate }}%</h3>
                        <p>成功率</p>
                    </div>
                    <div class="status-item">
                        <h3>⚡ {{ processed_count }}</h3>
                        <p>已处理</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- 文件上传卡片 -->
        <div class="card">
            <div class="card-header">📤 文件上传管理</div>
            <div class="card-body">
                <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
                    <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
                        <input type="file" id="fileInput" name="files" multiple accept="image/*">
                        <div class="upload-content" id="uploadContent">
                            <div id="defaultContent">
                                <h3>📁 点击选择图片或拖拽到此处</h3>
                                <p>支持 PNG, JPG, JPEG, GIF, BMP, WEBP 格式</p>
                                <p>最大文件大小: 16MB</p>
                            </div>
                            <div id="filesContent" style="display: none;">
                                <h3>📋 已选择文件</h3>
                                <div class="file-list-container" id="fileListContainer">
                                    <div class="file-list" id="fileList"></div>
                                </div>
                                <div class="files-summary" id="filesSummary">
                                    <div class="summary-item">
                                        <h4 id="fileCount">0</h4>
                                        <p>文件数量</p>
                                    </div>
                                    <div class="summary-item">
                                        <h4 id="totalSize">0 KB</h4>
                                        <p>总大小</p>
                                    </div>
                                    <div class="summary-item">
                                        <h4 id="avgSize">0 KB</h4>
                                        <p>平均大小</p>
                                    </div>
                                    <div class="summary-item">
                                        <h4 id="fileTypes">-</h4>
                                        <p>文件类型</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div style="text-align: center; margin: 20px 0;">
                        <button type="submit" class="btn btn-primary" id="uploadBtn" disabled>🚀 上传图片</button>
                        <button type="button" class="btn btn-secondary" onclick="clearSelection()">🗑️ 清除选择</button>
                        <button type="button" class="btn btn-secondary" onclick="refreshAll()">🔄 刷新列表</button>
                        <button type="button" class="btn btn-danger" onclick="confirmClearAll()">💥 清空所有</button>
                    </div>
                </form>
                <div id="uploadProgress" style="display: none;">
                    <div class="progress-bar">
                        <div id="progressFill" class="progress-fill" style="width: 0%;"></div>
                    </div>
                    <p id="uploadStatus">准备上传...</p>
                </div>
            </div>
        </div>

        <!-- 图片管理卡片 -->
        <div class="card">
            <div class="card-header">🖼️ 图片管理 ({{ total_images }}张)</div>
            <div class="card-body">
                {% if images %}
                <div class="image-gallery-container">
                    <div class="image-gallery">
                        {% for img in images %}
                        <div class="image-item" data-filename="{{ img.filename }}">
                            {% if img.exists %}
                            <img src="{{ img.url }}" alt="{{ img.filename }}" class="image-preview" 
                                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                            <div class="image-error-placeholder" style="display: none;">
                                <span>❌ 图片加载失败</span>
                            </div>
                            {% else %}
                            <div class="image-error-placeholder">
                                <span>❌ 文件不存在</span>
                            </div>
                            {% endif %}
                            <div class="image-info">
                                <h4>📄 {{ img.filename }}</h4>
                                {% if img.exists %}
                                <div class="url-display">🔗 {{ img.url }}</div>
                                {% endif %}
                                <p><strong>状态:</strong> 
                                    {% if img.exists %}
                                    <span style="color: green;">✅ 可用</span>
                                    {% else %}
                                    <span style="color: red;">❌ 不存在</span>
                                    {% endif %}
                                </p>
                            </div>
                            <div class="image-actions">
                                {% if img.exists %}
                                <a href="{{ img.url }}" target="_blank" class="btn btn-primary" style="font-size: 12px;">👁️ 预览</a>
                                <button onclick="copyUrl('{{ img.url }}')" class="btn btn-secondary" style="font-size: 12px;">📋 复制URL</button>
                                {% endif %}
                                <button onclick="deleteImage('{{ img.filename }}')" class="btn btn-danger" style="font-size: 12px;">🗑️ 删除</button>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% else %}
                <div style="text-align: center; padding: 40px; color: #666;">
                    <h3>📁 暂无图片</h3>
                    <p>请上传图片开始使用</p>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- 系统信息 -->
        <div class="card">
            <div class="card-header">💡 系统信息</div>
            <div class="card-body">
                <p><strong>🌐 服务地址:</strong> http://{{ host }}:{{ port }}</p>
                <p><strong>📁 图片目录:</strong> {{ image_folder }}</p>
                <p><strong>📄 CSV文件:</strong> {{ csv_path }}</p>
                <p><strong>🕒 最后更新:</strong> {{ current_time }}</p>
                <p><strong>📋 支持格式:</strong> PNG, JPG, JPEG, GIF, BMP, WEBP</p>
                <p><strong>📊 状态API:</strong> <a href="/status" target="_blank">{{ host }}:{{ port }}/status</a></p>
            </div>
        </div>

        <!-- 版权信息 -->
        <div class="footer">
            <h4>🎓 版权所有 &copy; 2024</h4>
            <div class="developer-info">
                <p><strong>🏫 开发单位:</strong> 中南大学交通运输工程学院</p>
                <p><strong>👨‍💻 开发者:</strong> 李响</p>
                <p><strong>📧 联系方式:</strong> 如有问题请联系开发者：xiangli@csu.edu.cn</p>
                <p><strong>🔧 版本信息:</strong> 图片URL服务器管理中心 v4.0 正式版</p>
            </div>
            <p style="margin-top: 15px; font-size: 0.9em; opacity: 0.8;">
                💡 本系统为学术研究与教学使用，请遵守相关使用规定
            </p>
        </div>
    </div>

    <!-- 确认删除模态框 -->
    <div id="deleteModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h3>⚠️ 确认删除</h3>
            <p id="deleteMessage">确定要删除这个图片吗？此操作不可恢复。</p>
            <div style="text-align: right; margin-top: 20px;">
                <button onclick="closeModal()" class="btn btn-secondary">❌ 取消</button>
                <button id="confirmDelete" class="btn btn-danger">✅ 删除</button>
            </div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        
        // 自动刷新倒计时
        let countdown = 30;
        const countdownEl = document.getElementById('refresh-countdown');
        const timer = setInterval(() => {
            countdown--;
            countdownEl.textContent = countdown;
            if (countdown <= 0) {
                location.reload();
            }
        }, 1000);

        // 文件选择处理
        document.getElementById('fileInput').addEventListener('change', function(e) {
            handleFileSelection(e.target.files);
        });

        function handleFileSelection(files) {
            selectedFiles = Array.from(files);
            updateFileDisplay();
        }

        function updateFileDisplay() {
            const uploadArea = document.getElementById('uploadArea');
            const defaultContent = document.getElementById('defaultContent');
            const filesContent = document.getElementById('filesContent');
            const fileList = document.getElementById('fileList');
            const uploadBtn = document.getElementById('uploadBtn');

            if (selectedFiles.length > 0) {
                uploadArea.classList.add('has-files');
                defaultContent.style.display = 'none';
                filesContent.style.display = 'block';
                uploadBtn.disabled = false;

                // 清空文件列表
                fileList.innerHTML = '';
                let totalSizeBytes = 0;
                const fileTypes = new Set();

                selectedFiles.forEach((file, index) => {
                    totalSizeBytes += file.size;
                    const extension = file.name.split('.').pop().toUpperCase();
                    fileTypes.add(extension);
                    
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.innerHTML = `
                        <div class="file-info">
                            <div class="file-name">📄 ${file.name}</div>
                            <div class="file-size">${formatFileSize(file.size)} | ${extension}</div>
                        </div>
                        <button type="button" class="remove-file" onclick="removeFile(${index})">❌ 移除</button>
                    `;
                    fileList.appendChild(fileItem);
                });

                // 更新统计信息
                updateFilesSummary(selectedFiles.length, totalSizeBytes, fileTypes);
            } else {
                uploadArea.classList.remove('has-files');
                defaultContent.style.display = 'block';
                filesContent.style.display = 'none';
                uploadBtn.disabled = true;
            }
        }

        function updateFilesSummary(count, totalBytes, fileTypes) {
            document.getElementById('fileCount').textContent = count;
            document.getElementById('totalSize').textContent = formatFileSize(totalBytes);
            document.getElementById('avgSize').textContent = formatFileSize(totalBytes / count);
            document.getElementById('fileTypes').textContent = Array.from(fileTypes).join(', ');
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileInput();
            updateFileDisplay();
        }

        function clearSelection() {
            selectedFiles = [];
            updateFileInput();
            updateFileDisplay();
        }

        function updateFileInput() {
            const dt = new DataTransfer();
            selectedFiles.forEach(file => dt.items.add(file));
            document.getElementById('fileInput').files = dt.files;
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
        });
        
        uploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFileSelection(files);
        }

        // 表单提交
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (selectedFiles.length === 0) {
                showAlert('error', '❌ 请先选择文件！');
                return;
            }
            
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            showProgress();
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            }).then(response => response.json())
            .then(data => {
                hideProgress();
                if (data.success) {
                    showAlert('success', `🎉 成功上传 ${data.uploaded_count} 个文件！`);
                    clearSelection();
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showAlert('error', '❌ 上传失败: ' + data.message);
                }
            }).catch(error => {
                hideProgress();
                showAlert('error', '❌ 上传失败: ' + error.message);
            });
        });

        // 进度条
        function showProgress() {
            document.getElementById('uploadProgress').style.display = 'block';
            document.getElementById('progressFill').style.width = '0%';
            document.getElementById('uploadStatus').textContent = '⏳ 正在上传...';
            
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress >= 90) {
                    clearInterval(progressInterval);
                    progress = 90;
                }
                document.getElementById('progressFill').style.width = progress + '%';
            }, 200);
        }
        
        function hideProgress() {
            document.getElementById('uploadProgress').style.display = 'none';
        }

        // 复制URL
        function copyUrl(url) {
            navigator.clipboard.writeText(url).then(() => {
                showAlert('success', '📋 URL已复制到剪贴板！');
            });
        }

        // 删除图片
        let deleteFilename = '';
        function deleteImage(filename) {
            deleteFilename = filename;
            document.getElementById('deleteMessage').textContent = `确定要删除 "${filename}" 吗？此操作不可恢复。`;
            document.getElementById('deleteModal').style.display = 'block';
        }
        
        document.getElementById('confirmDelete').onclick = function() {
            fetch('/delete/' + encodeURIComponent(deleteFilename), {method: 'DELETE'})
            .then(response => response.json())
            .then(data => {
                closeModal();
                if (data.success) {
                    showAlert('success', '🗑️ 文件删除成功！');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showAlert('error', '❌ 删除失败: ' + data.message);
                }
            });
        };

        function closeModal() {
            document.getElementById('deleteModal').style.display = 'none';
        }

        // 清空所有
        function confirmClearAll() {
            if (confirm('⚠️ 确定要清空所有图片吗？此操作不可恢复！')) {
                fetch('/clear_all', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('success', '💥 所有文件已清空！');
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        showAlert('error', '❌ 清空失败: ' + data.message);
                    }
                });
            }
        }

        // 刷新列表
        function refreshAll() {
            fetch('/refresh', {method: 'POST'})
            .then(() => location.reload());
        }

        // 下载CSV
        function downloadCSV() {
            window.open('/download_csv', '_blank');
        }

        // 显示提示
        function showAlert(type, message) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.textContent = message;
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.card'));
            setTimeout(() => alertDiv.remove(), 4000);
        }

        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('deleteModal');
            if (event.target == modal) {
                closeModal();
            }
        }
    </script>
</body>
</html>
"""

def allowed_file(filename):
    """检查文件扩展名是否被允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_uptime():
    """计算服务器运行时间"""
    if server_start_time:
        delta = datetime.now() - server_start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}小时{minutes}分钟"
    return "未知"

def scan_image_folder():
    """扫描图片目录并更新processed_images"""
    global processed_images
    base_url = f"http://{SERVER_HOST}:{SERVER_PORT}/images/"
    processed_images = []
    
    if not os.path.exists(IMAGE_FOLDER):
        return
    
    # 获取目录中的所有图片文件
    for filename in os.listdir(IMAGE_FOLDER):
        if allowed_file(filename):
            filepath = os.path.join(IMAGE_FOLDER, filename)
            processed_images.append({
                'filename': filename,
                'url': base_url + filename,
                'filepath': filepath,
                'exists': True
            })
    
    # 按文件名排序
    processed_images.sort(key=lambda x: x['filename'])

def safe_write_csv(csv_path, data_rows):
    """安全写入CSV文件，避免权限问题"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # 使用临时文件写入，然后重命名
        temp_path = csv_path + '.tmp'
        
        with open(temp_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['序号', '文件名', '图片URL', '更新时间'])
            writer.writerows(data_rows)
        
        # 重命名临时文件为目标文件
        if os.path.exists(csv_path):
            # 先备份原文件
            backup_path = CSV_BACKUP_PATH
            try:
                shutil.copy2(csv_path, backup_path)
                print(f"📦 已备份CSV文件到: {backup_path}")
            except Exception as e:
                print(f"⚠️  备份CSV文件失败: {e}")
        
        # 尝试重命名
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
            os.rename(temp_path, csv_path)
            print(f"✅ CSV文件已更新: {len(data_rows)} 个图片记录")
            return True
        except PermissionError:
            print(f"⚠️  CSV文件被占用，已保存到备份文件: {backup_path}")
            shutil.copy2(temp_path, backup_path)
            os.remove(temp_path)
            return False
        
    except Exception as e:
        print(f"❌ 更新CSV文件失败: {e}")
        return False

@app.route('/')
def home():
    """主页 - 显示管理界面"""
    scan_image_folder()  # 每次访问都重新扫描
    
    success_count = len([img for img in processed_images if img.get('exists', False)])
    success_rate = int((success_count / len(processed_images)) * 100) if processed_images else 100
    
    return render_template_string(HOME_TEMPLATE, 
        start_time=server_start_time.strftime('%Y-%m-%d %H:%M:%S') if server_start_time else '未知',
        uptime=calculate_uptime(),
        host=SERVER_HOST,
        port=SERVER_PORT,
        total_images=len(processed_images),
        processed_count=len(processed_images),
        success_rate=success_rate,
        images=processed_images,
        image_folder=IMAGE_FOLDER,
        csv_path=CSV_PATH,
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/upload', methods=['POST'])
def upload_files():
    """处理文件上传"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        files = request.files.getlist('files')
        uploaded_count = 0
        errors = []
        
        print(f"📤 开始处理 {len(files)} 个文件...")
        
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    # 生成唯一文件名避免冲突
                    base_name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(os.path.join(IMAGE_FOLDER, filename)):
                        filename = f"{base_name}_{counter}{ext}"
                        counter += 1
                    
                    filepath = os.path.join(IMAGE_FOLDER, filename)
                    file.save(filepath)
                    uploaded_count += 1
                    print(f"✅ 成功上传: {filename}")
                except Exception as e:
                    error_msg = f"上传 {file.filename} 失败: {str(e)}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            else:
                error_msg = f"文件 {file.filename} 格式不支持"
                errors.append(error_msg)
                print(f"⚠️  {error_msg}")
        
        # 更新CSV文件
        update_csv_file()
        
        message = f"成功上传 {uploaded_count} 个文件"
        if errors:
            message += f"，{len(errors)} 个失败"
        
        print(f"🎉 上传完成: {message}")
        
        return jsonify({
            'success': True,
            'message': message,
            'uploaded_count': uploaded_count,
            'errors': errors
        })
    
    except Exception as e:
        print(f"❌ 上传处理失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """删除指定文件"""
    try:
        print(f"🗑️  尝试删除文件: {filename}")
        filepath = os.path.join(IMAGE_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            update_csv_file()
            print(f"✅ 文件删除成功: {filename}")
            return jsonify({'success': True, 'message': f'文件 {filename} 删除成功'})
        else:
            print(f"❌ 文件不存在: {filename}")
            return jsonify({'success': False, 'message': '文件不存在'})
    except Exception as e:
        print(f"❌ 删除文件失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/clear_all', methods=['POST'])
def clear_all():
    """清空所有图片"""
    try:
        print("💥 开始清空所有图片...")
        if os.path.exists(IMAGE_FOLDER):
            shutil.rmtree(IMAGE_FOLDER)
            os.makedirs(IMAGE_FOLDER)
        update_csv_file()
        print("✅ 所有文件已清空")
        return jsonify({'success': True, 'message': '所有文件已清空'})
    except Exception as e:
        print(f"❌ 清空文件失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/refresh', methods=['POST'])
def refresh():
    """手动刷新"""
    print("🔄 手动刷新列表...")
    update_csv_file()
    return jsonify({'success': True})

@app.route('/download_csv')
def download_csv():
    """下载CSV文件"""
    try:
        if os.path.exists(CSV_PATH):
            return send_from_directory(os.path.dirname(CSV_PATH), 
                                     os.path.basename(CSV_PATH), 
                                     as_attachment=True)
        elif os.path.exists(CSV_BACKUP_PATH):
            print("⚠️  主CSV文件不存在，提供备份文件下载")
            return send_from_directory(os.path.dirname(CSV_BACKUP_PATH), 
                                     os.path.basename(CSV_BACKUP_PATH), 
                                     as_attachment=True)
        else:
            return jsonify({'error': 'CSV文件不存在'}), 404
    except Exception as e:
        print(f"❌ 下载CSV文件失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def status():
    """API接口 - 返回服务器状态JSON"""
    scan_image_folder()
    success_count = len([img for img in processed_images if img.get('exists', False)])
    
    status_data = {
        'status': 'running',
        'version': '4.0-正式版',
        'developer': {
            'institution': '中南大学交通运输工程学院',
            'name': '李响',
            'contact': '如有问题请联系开发者'
        },
        'server_info': {
            'start_time': server_start_time.isoformat() if server_start_time else None,
            'uptime_seconds': (datetime.now() - server_start_time).total_seconds() if server_start_time else 0,
            'uptime_formatted': calculate_uptime(),
            'host': SERVER_HOST,
            'port': SERVER_PORT,
            'image_folder': IMAGE_FOLDER,
            'csv_path': CSV_PATH,
            'csv_backup_path': CSV_BACKUP_PATH
        },
        'statistics': {
            'total_images': len(processed_images),
            'available_images': success_count,
            'success_rate': int((success_count / len(processed_images)) * 100) if processed_images else 100,
            'supported_formats': list(ALLOWED_EXTENSIONS),
            'max_file_size': '16MB'
        },
        'images': processed_images,
        'timestamp': datetime.now().isoformat(),
        'api_endpoints': {
            'home': f"http://{SERVER_HOST}:{SERVER_PORT}/",
            'upload': f"http://{SERVER_HOST}:{SERVER_PORT}/upload",
            'status': f"http://{SERVER_HOST}:{SERVER_PORT}/status",
            'download_csv': f"http://{SERVER_HOST}:{SERVER_PORT}/download_csv",
            'images_base_url': f"http://{SERVER_HOST}:{SERVER_PORT}/images/"
        }
    }
    
    return jsonify(status_data)

@app.route('/images/<filename>')
def serve_image(filename):
    """为图片提供HTTP访问接口"""
    try:
        return send_from_directory(IMAGE_FOLDER, filename)
    except Exception as e:
        print(f"❌ 图片访问失败: {filename} - {str(e)}")
        return jsonify({'error': f'图片不存在: {filename}'}), 404

def update_csv_file():
    """更新CSV文件"""
    scan_image_folder()
    try:
        print(f"💾 保存URL到CSV文件...")
        
        # 准备数据行
        data_rows = []
        for i, img in enumerate(processed_images, 1):
            if img['exists']:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data_rows.append([i, img['filename'], img['url'], timestamp])
        
        # 使用安全写入函数
        success = safe_write_csv(CSV_PATH, data_rows)
        
        if success:
            print(f"✅ CSV文件更新成功: {len(data_rows)} 个图片记录")
        else:
            print(f"⚠️  CSV文件被占用，已保存到备份文件")
        
    except Exception as e:
        print(f"❌ 更新CSV文件失败: {e}")

def save_server_status():
    """保存服务器状态到文件"""
    status_data = {
        'start_time': server_start_time.isoformat() if server_start_time else None,
        'host': SERVER_HOST,
        'port': SERVER_PORT,
        'image_folder': IMAGE_FOLDER,
        'processed_images': processed_images,
        'last_update': datetime.now().isoformat(),
        'version': '4.0-正式版',
        'developer': '李响 - 中南大学交通运输工程学院'
    }
    
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        print(f"💾 状态文件已保存: {STATUS_FILE}")
    except Exception as e:
        print(f"❌ 保存状态文件失败: {e}")

def signal_handler(sig, frame):
    """优雅关闭服务器"""
    print('\n' + "=" * 50)
    print('🛑 收到停止信号，正在保存状态并关闭服务器...')
    update_csv_file()
    save_server_status()
    print('✅ 服务器已停止')
    print("=" * 50)
    sys.exit(0)

def start_server():
    """启动Flask服务器"""
    global server_start_time
    server_start_time = datetime.now()
    
    print(f"🚀 启动Flask服务器...")
    print(f"🌐 地址: http://{SERVER_HOST}:{SERVER_PORT}")
    
    # 禁用Flask日志
    import logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, use_reloader=False)

def auto_update_csv():
    """定期更新CSV文件的后台任务"""
    while True:
        time.sleep(30)  # 每30秒更新一次
        try:
            update_csv_file()
        except Exception as e:
            print(f"❌ 自动更新CSV失败: {e}")

def main():
    """主函数"""
    print("=" * 70)
    print("🖼️  图片URL服务器管理中心 v4.0 正式版")
    print("🏫 开发单位: 中南大学交通运输工程学院")
    print("👨‍💻 开发者: 李响-xiangli@csu.edu.cn")
    print("=" * 70)
    print(f"📁 图片目录: {IMAGE_FOLDER}")
    print(f"📄 CSV文件: {CSV_PATH}")
    print(f"📦 备份文件: {CSV_BACKUP_PATH}")
    print(f"💾 状态文件: {STATUS_FILE}")
    
    # 确保目录存在
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    print(f"✅ 图片目录已准备就绪")
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 初始扫描
    scan_image_folder()
    
    # 初次更新CSV
    if processed_images:
        print(f"📊 发现 {len(processed_images)} 个现有图片")
        update_csv_file()
    
    # 启动自动更新CSV的后台线程
    csv_thread = threading.Thread(target=auto_update_csv, daemon=True)
    csv_thread.start()
    print(f"⚡ 自动CSV更新线程已启动")
    
    # 启动服务器
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print(f"🎉 服务器启动完成！")
    print(f"🌐 主页地址: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"📊 状态接口: http://{SERVER_HOST}:{SERVER_PORT}/status")
    print(f"💾 CSV下载: http://{SERVER_HOST}:{SERVER_PORT}/download_csv")
    print(f"✅ 成功处理: {len(processed_images)} 个图片")
    print(f"⚠️  保持程序运行以确保URL可访问")
    print(f"🛑 按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()
