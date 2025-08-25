# 🎼 基于BeatNet的智能曲谱生成功能设计

## 📝 项目概述

基于BeatNet深度学习模型实现"从一首歌新建曲谱"功能。采用纯深度学习方案，用户只需上传音频文件，系统将：

1. **BeatNet深度学习分析**：精确检测所有beat点和downbeat位置
2. **智能映射建议**：基于beat类型和强度智能建议don/ka分配
3. **用户确认界面**：直观的beat→note映射操作
4. **完美网格对齐**：生成的曲谱100%对齐beat网格

---

## 🏗️ 技术架构

### 核心优势
- **统一深度学习**：只依赖BeatNet一个模型，技术栈简洁
- **天然网格对齐**：beat检测结果自动对齐，无需后处理
- **高精度保证**：BeatNet深度学习确保beat检测准确性
- **用户友好**：映射过程直观（beat→note，而非复杂的音频分类）

### 架构流程
```
🎵 音频上传 → 🤖 BeatNet深度学习检测 → 💡 智能建议生成 → 👤 用户映射确认 → 📊 曲谱生成 → ✨ DAW编辑
```

---

## 👤 用户交互设计

### 3步简化流程

#### Step 1: 音频上传
```html
┌─────────────────────────────────┐
│ 🎼 从音频新建曲谱               │
├─────────────────────────────────┤  
│ 📤 拖拽音频文件到此处            │
│    或点击选择文件               │
│                                │
│ 支持格式: MP3, WAV, M4A         │
│ 项目名称: [____________]        │
│ 显示名称: [____________]        │
│                                │
│ [开始BeatNet分析 →]             │
└─────────────────────────────────┘
```

#### Step 2: BeatNet分析 (自动进行)
```html
┌─────────────────────────────────┐
│ 🤖 BeatNet深度学习分析中...      │
├─────────────────────────────────┤
│ ✅ 音频加载完成                  │
│ 🔄 深度学习beat检测... 73%      │ 
│ ⏳ 生成智能建议...               │
│                                │
│ 预计剩余时间: 15秒              │
└─────────────────────────────────┘
```

#### Step 3: Beat映射界面 (核心)
```html
┌─────────────────────────────────────────────────────────────┐
│ 🎯 Beat映射 - BeatNet检测到 68个beat点 (BPM: 128.5)         │
├─────────────────────────────────────────────────────────────┤
│ 🤖 智能建议：强拍→咚(17个) 普通拍→咔(51个)                   │
│ [应用全部建议] [只应用强拍→咚] [清除所有选择]                │
│                                                           │
│ 📊 Beat时间线预览 (可播放+滚动)                              │
│ ├─●─○─○─○─●─○─○─○─●─○─○─○─●─○─○─○─●─○─○─○─┤               │
│ 0.0s  1.0s  2.0s  3.0s  4.0s                            │
│ ▲         ▲         ▲    强拍(downbeat)                   │
│                                                           │
│ 🥁 Beat详细列表 (滚动查看)                                  │
│ ┌─────────────────────────────────────────────────────┐     │
│ │[●] 0.000s 强拍 强度:0.95 [咚][咔][跳过] 建议:咚     │     │  
│ │[○] 0.468s 普拍 强度:0.73 [咚][咔][跳过] 建议:咔     │     │
│ │[○] 0.937s 普拍 强度:0.71 [咚][咔][跳过] 建议:咔     │     │
│ │[○] 1.405s 普拍 强度:0.69 [咚][咔][跳过] 建议:咔     │     │
│ │[●] 1.874s 强拍 强度:0.91 [咚][咔][跳过] 建议:咚     │     │
│ │[○] 2.342s 普拍 强度:0.76 [咚][咔][跳过] 建议:咔     │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                           │
│ 📈 当前统计: 咚:0个 咔:0个 跳过:68个                        │
│ 🎵 [播放预览] [预览选中的音符]                              │
│                                                           │
│ [← 重新分析] [生成曲谱 →]                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 API设计详述

### 1. BeatNet全能分析API
```python
POST /api/beatnet-full-analysis
Content-Type: multipart/form-data

Request:
- audioFile: File
- projectName: string
- displayName: string

Response:
{
    "status": "success",
    "data": {
        "projectId": "uuid-string",
        "audioInfo": {
            "duration": 180.5,
            "sampleRate": 44100,
            "audioPath": "temp/uuid/audio.mp3"
        },
        "bpmData": {
            "bpm": 128.5,
            "confidence": 0.92,
            "method": "beatnet_deep_learning",
            "offset": -0.125,
            "r_squared": 0.94
        },
        "beatAnalysis": {
            "beats": [
                {
                    "index": 0,
                    "time": 0.000,
                    "type": "downbeat",        // "downbeat" | "beat"
                    "strength": 0.95,
                    "measureNumber": 1,
                    "beatInMeasure": 1,
                    "confidence": 0.92
                },
                {
                    "index": 1,
                    "time": 0.468,
                    "type": "beat",
                    "strength": 0.73,
                    "measureNumber": 1,
                    "beatInMeasure": 2,
                    "confidence": 0.89
                }
            ],
            "totalBeats": 68,
            "downbeatCount": 17,
            "totalMeasures": 17
        },
        "smartSuggestions": [
            {
                "beatIndex": 0,
                "suggestion": "don",       // "don" | "ka" | "skip"
                "confidence": 0.85,
                "reason": "downbeat_high_strength"
            },
            {
                "beatIndex": 1,
                "suggestion": "ka",
                "confidence": 0.65,
                "reason": "beat_medium_strength"
            }
        ],
        "suggestionStats": {
            "suggestedDon": 17,
            "suggestedKa": 35,
            "suggestedSkip": 16
        }
    }
}
```

### 2. 处理用户映射选择
```python
POST /api/process-beat-mapping

Request:
{
    "projectId": "uuid-string",
    "mappings": [
        {"beatIndex": 0, "userChoice": "don"},
        {"beatIndex": 1, "userChoice": "ka"},
        {"beatIndex": 2, "userChoice": "skip"},
        {"beatIndex": 3, "userChoice": "don"}
    ],
    "settings": {
        "snapToGrid": true,        // 总是true，因为基于beat
        "preserveOffset": true
    }
}

Response:
{
    "status": "success",
    "data": {
        "generatedScore": [
            {
                "id": "score_000",
                "time": 0.000,            // 直接使用beat时间
                "type": "don",
                "originalBeatIndex": 0,
                "beatType": "downbeat",
                "strength": 0.95,
                "measurePosition": 1
            },
            {
                "id": "score_001", 
                "time": 0.468,
                "type": "ka",
                "originalBeatIndex": 1,
                "beatType": "beat",
                "strength": 0.73,
                "measurePosition": 1
            }
        ],
        "scoreStats": {
            "totalNotes": 43,
            "donCount": 15,
            "kaCount": 28,
            "averageNoteStrength": 0.78,
            "strongBeatUtilization": 0.88,    // 17/17强拍被使用
            "regularBeatUtilization": 0.55    // 28/51普拍被使用
        },
        "qualityMetrics": {
            "rhythmComplexity": 0.65,         // 节奏复杂度
            "beatCoverage": 0.63,             // beat覆盖率
            "downbeatAlignment": 1.0          // 强拍对齐度(总是1.0)
        }
    }
}
```

### 3. 保存最终项目
```python
POST /api/finalize-beatnet-project

Request:
{
    "projectId": "uuid-string",
    "finalScore": [...],           // 来自上一步的generatedScore
    "metadata": {
        "userMappingTime": 180,    // 用户映射耗时(秒)
        "totalAdjustments": 12,    // 用户手动调整次数
        "suggestionAcceptRate": 0.73
    }
}

Response:
{
    "status": "success",
    "data": {
        "savedProjectName": "my_new_song",
        "projectPath": "data/my_new_song/",
        "scoreFile": "data/my_new_song/score/score.json",
        "metadataFile": "data/my_new_song/metadata.json",
        "redirectUrl": "/daw?project=my_new_song"
    }
}
```

---

## ⚙️ 后端实现详述

### 1. BeatNet集成服务
```python
class BeatNetScoreGenerator:
    """基于BeatNet的曲谱生成器"""
    
    def __init__(self):
        self.beatnet = BeatNet(1, mode='offline', inference_model='DBN', plot=[], thread=False)
        
    async def analyze_audio_full(self, audio_path: str, project_name: str) -> dict:
        """完整的BeatNet音频分析"""
        
        # 1. BeatNet深度学习检测
        output = self.beatnet.process(audio_path)
        
        if output is None or len(output) == 0:
            raise RuntimeError("BeatNet failed to detect any beats")
            
        beat_times = output[:, 0]  # 时间戳
        beat_types = output[:, 1]  # 1=downbeat, 2=beat
        
        # 2. 计算BPM和置信度
        bpm_data = self._calculate_bpm_metrics(beat_times)
        
        # 3. 生成详细beat分析
        beat_analysis = self._generate_beat_analysis(beat_times, beat_types)
        
        # 4. 生成智能建议
        smart_suggestions = self._generate_smart_suggestions(beat_analysis['beats'])
        
        return {
            'bpmData': bpm_data,
            'beatAnalysis': beat_analysis,
            'smartSuggestions': smart_suggestions,
            'suggestionStats': self._calculate_suggestion_stats(smart_suggestions)
        }
    
    def _generate_beat_analysis(self, beat_times: np.ndarray, beat_types: np.ndarray) -> dict:
        """生成详细的beat分析数据"""
        beats = []
        current_measure = 1
        beats_in_current_measure = 0
        
        for i, (time, beat_type) in enumerate(zip(beat_times, beat_types)):
            # 检测新小节开始 (downbeat)
            if beat_type == 1:  # downbeat
                if i > 0:  # 不是第一个beat
                    current_measure += 1
                beats_in_current_measure = 1
                type_str = "downbeat"
            else:  # regular beat
                beats_in_current_measure += 1
                type_str = "beat"
            
            # 计算beat强度 (可以基于BeatNet的内部机制或音频分析)
            strength = self._calculate_beat_strength(time, beat_type)
            
            beats.append({
                'index': i,
                'time': float(time),
                'type': type_str,
                'strength': strength,
                'measureNumber': current_measure,
                'beatInMeasure': beats_in_current_measure,
                'confidence': 0.9  # BeatNet输出通常很可靠
            })
        
        return {
            'beats': beats,
            'totalBeats': len(beats),
            'downbeatCount': len(np.where(beat_types == 1)[0]),
            'totalMeasures': current_measure
        }
    
    def _generate_smart_suggestions(self, beats: List[dict]) -> List[dict]:
        """生成智能映射建议"""
        suggestions = []
        
        for beat in beats:
            if beat['type'] == 'downbeat':
                # 强拍优先建议咚
                suggestion = 'don'
                confidence = 0.85
                reason = 'downbeat_high_priority'
                
            elif beat['strength'] > 0.75:
                # 高强度普通拍建议咔
                suggestion = 'ka'
                confidence = 0.70
                reason = 'beat_high_strength'
                
            elif beat['strength'] > 0.60:
                # 中等强度普通拍建议咔
                suggestion = 'ka' 
                confidence = 0.55
                reason = 'beat_medium_strength'
                
            else:
                # 低强度拍建议跳过
                suggestion = 'skip'
                confidence = 0.40
                reason = 'beat_low_strength'
            
            suggestions.append({
                'beatIndex': beat['index'],
                'suggestion': suggestion,
                'confidence': confidence,
                'reason': reason
            })
        
        return suggestions
    
    def _calculate_beat_strength(self, time: float, beat_type: int) -> float:
        """计算beat强度 (简化实现，实际可能需要音频分析)"""
        if beat_type == 1:  # downbeat
            return np.random.uniform(0.85, 0.95)  # 强拍通常强度较高
        else:  # regular beat
            return np.random.uniform(0.60, 0.85)  # 普通拍强度变化较大
    
    def process_user_mapping(self, beat_data: List[dict], mappings: List[dict]) -> dict:
        """处理用户的映射选择，生成最终曲谱"""
        generated_score = []
        mapping_dict = {m['beatIndex']: m['userChoice'] for m in mappings}
        
        for beat in beat_data:
            beat_index = beat['index']
            user_choice = mapping_dict.get(beat_index, 'skip')
            
            if user_choice in ['don', 'ka']:
                score_item = {
                    'id': f"score_{beat_index:03d}",
                    'time': beat['time'],  # 直接使用BeatNet检测的精确时间
                    'type': user_choice,
                    'originalBeatIndex': beat_index,
                    'beatType': beat['type'],
                    'strength': beat['strength'],
                    'measurePosition': beat['measureNumber']
                }
                generated_score.append(score_item)
        
        # 计算统计信息
        score_stats = self._calculate_score_stats(generated_score, beat_data)
        
        return {
            'generatedScore': generated_score,
            'scoreStats': score_stats,
            'qualityMetrics': self._calculate_quality_metrics(generated_score, beat_data)
        }
```

### 2. 项目管理服务
```python
class BeatNetProjectManager:
    """BeatNet项目管理器"""
    
    def __init__(self, base_path: str = "data/"):
        self.base_path = base_path
        self.temp_projects = {}
        self.score_generator = BeatNetScoreGenerator()
    
    async def create_and_analyze_project(self, audio_file, project_name: str, 
                                       display_name: str) -> dict:
        """创建项目并进行BeatNet分析"""
        project_id = str(uuid.uuid4())
        
        # 创建临时目录保存音频
        temp_dir = f"temp/{project_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        audio_path = os.path.join(temp_dir, "audio.mp3")
        await self._save_uploaded_file(audio_file, audio_path)
        
        # 获取音频基本信息
        y, sr = librosa.load(audio_path, sr=None)
        duration = len(y) / sr
        
        # BeatNet全面分析
        analysis_result = await self.score_generator.analyze_audio_full(
            audio_path, project_name
        )
        
        # 保存项目数据到缓存
        project_data = {
            'projectId': project_id,
            'projectName': project_name,
            'displayName': display_name,
            'audioPath': audio_path,
            'audioInfo': {
                'duration': duration,
                'sampleRate': int(sr)
            },
            'createdAt': datetime.now().isoformat(),
            **analysis_result
        }
        
        self.temp_projects[project_id] = project_data
        
        return project_data
    
    async def finalize_project(self, project_id: str, final_score: List[dict], 
                             user_metadata: dict) -> dict:
        """完成项目创建并保存到最终位置"""
        if project_id not in self.temp_projects:
            raise ValueError(f"Project {project_id} not found")
        
        project_data = self.temp_projects[project_id]
        project_name = project_data['projectName']
        
        # 创建最终项目目录
        final_dir = os.path.join(self.base_path, project_name)
        os.makedirs(final_dir, exist_ok=True)
        
        # 移动音频文件
        final_audio_path = os.path.join(final_dir, f"{project_name}.mp3")
        shutil.move(project_data['audioPath'], final_audio_path)
        
        # 保存曲谱
        score_dir = os.path.join(final_dir, 'score')
        os.makedirs(score_dir, exist_ok=True)
        
        score_data = {
            'metadata': {
                'projectId': project_id,
                'creationMethod': 'beatnet_generation',
                'beatnetVersion': 'DBN_v1.0',
                'generatedAt': datetime.now().isoformat(),
                'bpmData': project_data['bpmData'],
                **user_metadata
            },
            'notes': final_score
        }
        
        score_file = os.path.join(score_dir, 'score.json')
        with open(score_file, 'w', encoding='utf-8') as f:
            json.dump(score_data, f, indent=2, ensure_ascii=False)
        
        # 保存项目元数据
        metadata_file = os.path.join(final_dir, 'metadata.json') 
        project_metadata = {
            'project_name': project_name,
            'display_name': project_data['displayName'],
            'audio_file': f"{project_name}.mp3",
            'creation_method': 'beatnet_smart_generation',
            'bmp_data': project_data['bmpData'],  # 保持兼容性
            'created_at': project_data['createdAt'],
            'finalized_at': datetime.now().isoformat()
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(project_metadata, f, indent=2, ensure_ascii=False)
        
        # 清理临时数据
        temp_dir = os.path.dirname(project_data['audioPath'])
        shutil.rmtree(temp_dir, ignore_errors=True)
        del self.temp_projects[project_id]
        
        return {
            'savedProjectName': project_name,
            'projectPath': final_dir,
            'scoreFile': score_file,
            'metadataFile': metadata_file,
            'redirectUrl': f'/daw?project={project_name}'
        }
```

---

## 🎨 前端实现详述

### 1. BeatNet映射界面组件
```javascript
class BeatNetMappingInterface {
    constructor(projectData) {
        this.projectId = projectData.projectId;
        this.beats = projectData.beatAnalysis.beats;
        this.suggestions = projectData.smartSuggestions;
        this.bpmData = projectData.bpmData;
        
        this.userMappings = new Map();
        this.selectedBeats = new Set();
        
        this.initializeInterface();
    }
    
    initializeInterface() {
        this.renderHeader();
        this.renderSmartSuggestions();
        this.renderTimeline();
        this.renderBeatList();
        this.renderControls();
    }
    
    renderHeader() {
        const headerHtml = `
            <div class="beatnet-header">
                <h2>🎯 Beat映射 - BeatNet检测到 ${this.beats.length}个beat点</h2>
                <div class="bpm-info">
                    <span class="bpm">BPM: ${this.bmpData.bpm.toFixed(1)}</span>
                    <span class="confidence">置信度: ${(this.bmpData.confidence * 100).toFixed(0)}%</span>
                </div>
            </div>
        `;
        document.getElementById('mapping-header').innerHTML = headerHtml;
    }
    
    renderSmartSuggestions() {
        const stats = this.calculateSuggestionStats();
        const suggestionsHtml = `
            <div class="smart-suggestions">
                <div class="suggestion-text">
                    🤖 智能建议：强拍→咚(${stats.don}个) 普通拍→咔(${stats.ka}个) 跳过(${stats.skip}个)
                </div>
                <div class="suggestion-actions">
                    <button class="btn btn-primary" id="apply-all-suggestions">
                        应用全部建议
                    </button>
                    <button class="btn btn-secondary" id="apply-downbeat-only">
                        只应用强拍→咚
                    </button>
                    <button class="btn btn-secondary" id="clear-all-mappings">
                        清除所有选择
                    </button>
                </div>
            </div>
        `;
        document.getElementById('suggestions-panel').innerHTML = suggestionsHtml;
        this.attachSuggestionHandlers();
    }
    
    renderTimeline() {
        const timelineContainer = document.getElementById('beat-timeline');
        const duration = this.beats[this.beats.length - 1].time + 2; // 加2秒缓冲
        const pxPerSecond = 100; // 每秒100px
        const totalWidth = duration * pxPerSecond;
        
        let timelineHtml = `
            <div class="timeline-track" style="width: ${totalWidth}px;">
                <div class="timeline-grid">
        `;
        
        // 绘制beat点
        this.beats.forEach(beat => {
            const position = beat.time * pxPerSecond;
            const isDownbeat = beat.type === 'downbeat';
            const classes = isDownbeat ? 'beat-marker downbeat' : 'beat-marker';
            
            timelineHtml += `
                <div class="${classes}" 
                     style="left: ${position}px;" 
                     data-beat-index="${beat.index}"
                     title="${beat.type} at ${beat.time.toFixed(3)}s">
                    ${isDownbeat ? '●' : '○'}
                </div>
            `;
        });
        
        timelineHtml += `
                </div>
                <div class="timeline-ruler">
                    <!-- 时间刻度 -->
                </div>
            </div>
        `;
        
        timelineContainer.innerHTML = timelineHtml;
        this.attachTimelineHandlers();
    }
    
    renderBeatList() {
        const listContainer = document.getElementById('beat-list');
        let listHtml = '';
        
        this.beats.forEach(beat => {
            const suggestion = this.suggestions.find(s => s.beatIndex === beat.index);
            const userMapping = this.userMappings.get(beat.index) || 'none';
            
            listHtml += `
                <div class="beat-item" data-beat-index="${beat.index}">
                    <div class="beat-info">
                        <div class="beat-marker ${beat.type}">
                            ${beat.type === 'downbeat' ? '●' : '○'}
                        </div>
                        <div class="beat-details">
                            <div class="time">${beat.time.toFixed(3)}s</div>
                            <div class="type">${beat.type === 'downbeat' ? '强拍' : '普拍'}</div>
                            <div class="strength">强度: ${beat.strength.toFixed(2)}</div>
                        </div>
                    </div>
                    <div class="mapping-controls">
                        <button class="mapping-btn ${userMapping === 'don' ? 'selected' : ''}" 
                                data-choice="don">咚</button>
                        <button class="mapping-btn ${userMapping === 'ka' ? 'selected' : ''}" 
                                data-choice="ka">咔</button>
                        <button class="mapping-btn ${userMapping === 'skip' ? 'selected' : ''}" 
                                data-choice="skip">跳过</button>
                    </div>
                    <div class="suggestion-hint">
                        建议: ${suggestion ? this.getSuggestionText(suggestion.suggestion) : '无'}
                    </div>
                </div>
            `;
        });
        
        listContainer.innerHTML = listHtml;
        this.attachMappingHandlers();
    }
    
    applyAllSuggestions() {
        this.suggestions.forEach(suggestion => {
            this.userMappings.set(suggestion.beatIndex, suggestion.suggestion);
        });
        this.updateUI();
        this.updateStats();
        toastManager.success(`已应用${this.suggestions.length}个智能建议`);
    }
    
    applyDownbeatSuggestions() {
        this.suggestions
            .filter(s => s.suggestion === 'don')
            .forEach(suggestion => {
                this.userMappings.set(suggestion.beatIndex, 'don');
            });
        this.updateUI();
        this.updateStats();
        const downbeatCount = this.suggestions.filter(s => s.suggestion === 'don').length;
        toastManager.success(`已应用${downbeatCount}个强拍建议`);
    }
    
    async generateScore() {
        const mappings = Array.from(this.userMappings.entries()).map(([beatIndex, userChoice]) => ({
            beatIndex,
            userChoice
        }));
        
        if (mappings.length === 0) {
            toastManager.warning('请至少选择一些beat进行映射');
            return;
        }
        
        try {
            showLoading('生成曲谱中...');
            
            const response = await fetch('/api/process-beat-mapping', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    projectId: this.projectId,
                    mappings: mappings,
                    settings: {
                        snapToGrid: true,
                        preserveOffset: true
                    }
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showScorePreview(result.data);
            } else {
                throw new Error(result.message || '生成曲谱失败');
            }
        } catch (error) {
            toastManager.error(`生成失败: ${error.message}`);
        } finally {
            hideLoading();
        }
    }
}
```

### 2. 曲谱预览和最终确认
```javascript
class ScorePreviewModal {
    constructor(scoreData, projectData) {
        this.scoreData = scoreData;
        this.projectData = projectData;
        this.isPlaying = false;
        
        this.showModal();
    }
    
    showModal() {
        const modalHtml = `
            <div class="score-preview-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>✨ 曲谱生成完成!</h2>
                        <button class="close-btn">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="score-stats">
                            <div class="stat-item">
                                <span class="label">总音符数:</span>
                                <span class="value">${this.scoreData.scoreStats.totalNotes}个</span>
                            </div>
                            <div class="stat-item">
                                <span class="label">咚音符:</span>
                                <span class="value">${this.scoreData.scoreStats.donCount}个</span>
                            </div>
                            <div class="stat-item">
                                <span class="label">咔音符:</span>
                                <span class="value">${this.scoreData.scoreStats.kaCount}个</span>
                            </div>
                            <div class="stat-item">
                                <span class="label">BPM:</span>
                                <span class="value">${this.projectData.bmpData.bpm.toFixed(1)}</span>
                            </div>
                        </div>
                        
                        <div class="quality-metrics">
                            <h3>质量评估</h3>
                            <div class="metric">
                                <span>强拍对齐度: ${(this.scoreData.qualityMetrics.downbeatAlignment * 100).toFixed(0)}%</span>
                                <div class="progress-bar">
                                    <div class="progress" style="width: ${this.scoreData.qualityMetrics.downbeatAlignment * 100}%"></div>
                                </div>
                            </div>
                            <div class="metric">
                                <span>Beat覆盖率: ${(this.scoreData.qualityMetrics.beatCoverage * 100).toFixed(0)}%</span>
                                <div class="progress-bar">
                                    <div class="progress" style="width: ${this.scoreData.qualityMetrics.beatCoverage * 100}%"></div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="preview-controls">
                            <button class="btn btn-primary" id="play-preview">
                                🎵 播放预览
                            </button>
                            <button class="btn btn-secondary" id="export-midi">
                                📝 导出MIDI
                            </button>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="back-to-mapping">
                            ← 重新调整
                        </button>
                        <button class="btn btn-primary" id="finalize-project">
                            进入DAW编辑器
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        this.attachHandlers();
    }
    
    async finalizeProject() {
        try {
            showLoading('保存项目中...');
            
            const response = await fetch('/api/finalize-beatnet-project', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    projectId: this.projectData.projectId,
                    finalScore: this.scoreData.generatedScore,
                    metadata: {
                        userMappingTime: this.calculateMappingTime(),
                        totalAdjustments: this.countUserAdjustments(),
                        suggestionAcceptRate: this.calculateAcceptRate()
                    }
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                toastManager.success('项目保存成功!');
                // 跳转到DAW编辑器
                window.location.href = result.data.redirectUrl;
            } else {
                throw new Error(result.message || '保存项目失败');
            }
        } catch (error) {
            toastManager.error(`保存失败: ${error.message}`);
        } finally {
            hideLoading();
        }
    }
}
```

---

## 📅 开发计划

### Phase 1: BeatNet后端集成 (1.5周)
- [ ] 扩展现有BeatNet检测API支持完整分析
- [ ] 实现智能建议生成算法
- [ ] 开发beat映射处理逻辑
- [ ] 创建项目管理和持久化服务

### Phase 2: 前端映射界面 (1.5周)  
- [ ] 创建多步骤向导框架
- [ ] 实现beat可视化时间线
- [ ] 开发交互式映射界面
- [ ] 添加实时预览和统计功能

### Phase 3: 集成与优化 (1周)
- [ ] 与现有DAW界面集成
- [ ] 性能优化和错误处理
- [ ] 用户体验微调
- [ ] 全流程测试

**总预估工时：4周**

---

## 🎯 关键成功指标

### 技术指标
- **Beat检测准确率**：≥95% (BeatNet深度学习保证)
- **用户映射效率**：平均映射时间 ≤3分钟/首歌
- **网格对齐精度**：100% (直接基于beat时间)
- **处理性能**：3分钟音频 ≤15秒BeatNet分析

### 用户体验指标
- **智能建议接受率**：≥70% 用户接受AI建议
- **向导完成率**：≥90% 用户完成整个流程  
- **重新调整率**：≤20% 用户大幅修改建议
- **功能满意度**：≥4.5/5.0 用户评分

## 🚀 技术优势总结

1. **深度学习准确性**：BeatNet提供最高精度的beat检测
2. **完美网格对齐**：生成的曲谱天然对齐beat网格
3. **用户友好体验**：直观的beat→note映射过程
4. **技术栈统一**：只依赖BeatNet，维护简单
5. **快速处理**：无需复杂特征工程，处理速度快

这个基于BeatNet的纯深度学习方案将大幅提升曲谱制作的效率和质量！