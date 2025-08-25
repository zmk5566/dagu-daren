#!/usr/bin/env python3
"""
测试新的BeatNet到annotation再到score的转换管线
"""

def test_conversion_pipeline():
    # 模拟BeatNet检测到的notes
    beatnet_notes = [
        {'time': 0.2, 'type': 'don', 'originalBeatIndex': 0},
        {'time': 0.86, 'type': 'ka', 'originalBeatIndex': 1},
        {'time': 1.5, 'type': 'don', 'originalBeatIndex': 2},
        {'time': 2.16, 'type': 'ka', 'originalBeatIndex': 3},
    ]
    
    project_data = {'projectId': 'test_123'}
    
    # 调用转换函数
    from server import convert_beatnet_to_annotations_then_score
    result = convert_beatnet_to_annotations_then_score(beatnet_notes, project_data)
    
    print("=== 转换结果 ===")
    for i, note in enumerate(result):
        print(f"Note {i+1}: time={note['time']:.3f}s, type={note['type']}, duration={note['duration']}s, id={note['id'][:20]}...")
    
    # 验证格式
    assert len(result) == len(beatnet_notes), "音符数量不匹配"
    assert all('time' in note for note in result), "缺少time字段"
    assert all('type' in note for note in result), "缺少type字段" 
    assert all('duration' in note for note in result), "缺少duration字段"
    assert all('id' in note for note in result), "缺少id字段"
    assert all(note['duration'] == 0.1 for note in result), "音符长度不是0.1秒"
    
    print("✅ 转换管线测试通过!")

if __name__ == '__main__':
    test_conversion_pipeline()