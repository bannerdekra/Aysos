import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

TOOL_SCHEMA = {
    'type': 'function',
    'function': {
        'name': 'get_system_time',
        'description': '获取当前系统时间，包括日期、时间、星期、时区等信息',
        'parameters': {
            'type': 'object',
            'properties': {
                'timezone': {
                    'type': 'string',
                    'description': '时区名称（例如：Asia/Shanghai、UTC、America/New_York），默认使用本地时区'
                },
                'format': {
                    'type': 'string',
                    'description': '时间格式（iso、timestamp、readable），默认：readable'
                }
            },
            'required': []
        }
    }
}

def get_system_time(timezone=None, format='readable'):
    try:
        if timezone:
            current_time = datetime.now(ZoneInfo(timezone))
        else:
            current_time = datetime.now()
        
        weekday_index = current_time.weekday()
        weekday_en_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_cn_list = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday_en = weekday_en_list[weekday_index]
        weekday_cn = weekday_cn_list[weekday_index]
        
        result = {
            'date': current_time.strftime('%Y-%m-%d'),
            'time': current_time.strftime('%H:%M:%S'),
            'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'weekday': weekday_en,
            'weekday_cn': weekday_cn,
            'timezone': str(current_time.tzinfo) if current_time.tzinfo else 'local',
            'timestamp': int(current_time.timestamp()),
            'iso_format': current_time.isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)
