import pyodbc
import uuid

class DatabaseManager:
    def __init__(self, dsn_name):
        self.dsn_name = dsn_name
        self.conn_str = f'DSN={dsn_name};'
        try:
            self.conn = pyodbc.connect(self.conn_str)
            self.cursor = self.conn.cursor()
            self._create_tables()
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            if sqlstate == '28000':
                print("认证失败：DSN 中的用户名或密码错误。")
            else:
                print(f"数据库连接失败：{ex}")
            raise  # 重新抛出异常，让调用者处理
    
    @staticmethod
    def test_dsn_connection(dsn_name):
        """测试DSN连接"""
        try:
            conn_str = f'DSN={dsn_name};'
            conn = pyodbc.connect(conn_str)
            # 执行一个简单的查询来确保连接正常
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            return True, "DSN连接成功！"
        except pyodbc.Error as ex:
            sqlstate = ex.args[0] if ex.args else 'Unknown'
            if sqlstate == '28000':
                return False, "认证失败：DSN中的用户名或密码错误"
            elif sqlstate == 'IM002':
                return False, f"数据源名称'{dsn_name}'未找到，请检查DSN配置"
            else:
                return False, f"连接失败：{str(ex)}"
        except Exception as ex:
            return False, f"连接失败：{str(ex)}"
    
    def _create_tables(self):
        # 创建 conversations 表来存储对话信息
        self.cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversations' AND xtype='U')
            CREATE TABLE conversations (
                id VARCHAR(36) PRIMARY KEY,
                title NVARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT GETDATE()
            )
        ''')
        
        # 修改 messages 表，增加 conversation_id
        self.cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE Name = N'conversation_id' AND Object_ID = Object_ID(N'messages'))
            BEGIN
                ALTER TABLE messages ADD conversation_id VARCHAR(36);
                ALTER TABLE messages ADD CONSTRAINT FK_messages_conversations FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;
            END
        ''')
        self.conn.commit()

    def create_new_conversation(self, title="新对话"):
        new_id = str(uuid.uuid4())
        self.cursor.execute('INSERT INTO conversations (id, title) VALUES (?, ?)', (new_id, title))
        self.conn.commit()
        return new_id
    
    def update_conversation_title(self, conversation_id, new_title):
        self.cursor.execute('UPDATE conversations SET title = ? WHERE id = ?', (new_title, conversation_id))
        self.conn.commit()

    def delete_conversation(self, conversation_id):
        # ON DELETE CASCADE 会自动删除messages表中所有相关的记录
        self.cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
        self.conn.commit()

    def get_all_conversations(self):
        self.cursor.execute('SELECT id, title, created_at FROM conversations ORDER BY created_at DESC')
        return self.cursor.fetchall()
    
    def get_latest_conversation(self):
        """获取最新的对话"""
        self.cursor.execute('SELECT id, title, created_at FROM conversations ORDER BY created_at DESC')
        result = self.cursor.fetchone()
        return result if result else None

    def add_message(self, conversation_id, role, content):
        self.cursor.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)', (conversation_id, role, content))
        self.conn.commit()

    def get_history(self, conversation_id):
        if not conversation_id:
            return []
        self.cursor.execute('SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC', (conversation_id,))
        return [{'role': row.role, 'content': row.content} for row in self.cursor.fetchall()]

    def delete_messages_from_index(self, conversation_id, start_index):
        """删除从指定索引开始的所有消息"""
        self.cursor.execute('''
            DELETE FROM messages 
            WHERE conversation_id = ? 
            AND id >= (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY id ASC) as rn 
                    FROM messages 
                    WHERE conversation_id = ?
                ) as numbered 
                WHERE rn = ?
            )
        ''', (conversation_id, conversation_id, start_index + 1))
        self.conn.commit()

    def delete_message_by_index(self, conversation_id, message_index):
        """删除指定索引的单条消息"""
        print(f"数据库删除消息: 对话ID={conversation_id}, 索引={message_index}")
        
        # 先查看当前消息数量
        self.cursor.execute('SELECT COUNT(*) FROM messages WHERE conversation_id = ?', (conversation_id,))
        count = self.cursor.fetchone()[0]
        print(f"删除前消息数量: {count}")
        
        # 使用改进的删除查询
        self.cursor.execute('''
            WITH numbered_messages AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY id ASC) as rn
                FROM messages 
                WHERE conversation_id = ?
            )
            DELETE FROM messages 
            WHERE id = (
                SELECT id FROM numbered_messages WHERE rn = ?
            )
        ''', (conversation_id, message_index + 1))
        
        affected_rows = self.cursor.rowcount
        self.conn.commit()
        
        print(f"删除操作影响行数: {affected_rows}")
        
        # 再次查看消息数量确认删除成功
        self.cursor.execute('SELECT COUNT(*) FROM messages WHERE conversation_id = ?', (conversation_id,))
        new_count = self.cursor.fetchone()[0]
        print(f"删除后消息数量: {new_count}")

    def close(self):
        self.conn.close()