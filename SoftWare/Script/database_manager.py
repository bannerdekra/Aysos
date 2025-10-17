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
        """初始化数据表结构，并确保字段类型满足需求"""
        dbms_name = ""
        try:
            dbms_name = (self.conn.getinfo(pyodbc.SQL_DBMS_NAME) or "").strip()
            if dbms_name:
                print(f"[数据库] 当前数据源: {dbms_name}")
        except Exception as exc:
            print(f"[数据库] 无法获取数据源类型: {exc}")
        upper_dbms = dbms_name.upper()

        # SQL Server 专用的建表语句在其他数据库会失败，故做防护
        def execute_safe(sql: str):
            try:
                self.cursor.execute(sql)
            except pyodbc.Error as ex:
                if 'SQL SERVER' in upper_dbms:
                    print(f"[数据库] SQL Server 语句执行失败: {ex}")

        # 兼容旧版本：尝试执行 SQL Server 风格的建表/加列语句
        execute_safe('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversations' AND xtype='U')
            CREATE TABLE conversations (
                id VARCHAR(36) PRIMARY KEY,
                title NVARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT GETDATE()
            )
        ''')

        execute_safe('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE Name = N'conversation_id' AND Object_ID = Object_ID(N'messages'))
            BEGIN
                ALTER TABLE messages ADD conversation_id VARCHAR(36);
                ALTER TABLE messages ADD CONSTRAINT FK_messages_conversations FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;
            END
        ''')

        execute_safe('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE Name = N'files' AND Object_ID = Object_ID(N'messages'))
            BEGIN
                ALTER TABLE messages ADD files NVARCHAR(MAX);
            END
        ''')

        # 针对非 SQL Server 数据库，使用 ODBC 元数据判断表/列是否存在
        try:
            existing_tables = set()
            for tbl in self.cursor.tables(tableType='TABLE'):
                if tbl.table_name:
                    existing_tables.add(tbl.table_name.lower())

            if 'conversations' not in existing_tables:
                if 'ACCESS' in upper_dbms:
                    create_sql = '''CREATE TABLE conversations (
                        id TEXT(36) PRIMARY KEY,
                        title TEXT(255),
                        created_at DATETIME
                    )'''
                else:
                    create_sql = '''CREATE TABLE conversations (
                        id VARCHAR(36) PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        created_at DATETIME
                    )'''
                print("[数据库] 创建 conversations 表")
                self.cursor.execute(create_sql)

            if 'messages' not in existing_tables:
                if 'ACCESS' in upper_dbms:
                    create_sql = '''CREATE TABLE messages (
                        id AUTOINCREMENT PRIMARY KEY,
                        conversation_id TEXT(36),
                        role TEXT(50),
                        content LONGTEXT,
                        files LONGTEXT
                    )'''
                else:
                    create_sql = '''CREATE TABLE messages (
                        id INTEGER PRIMARY KEY,
                        conversation_id VARCHAR(36),
                        role VARCHAR(50),
                        content TEXT,
                        files TEXT
                    )'''
                print("[数据库] 创建 messages 表")
                self.cursor.execute(create_sql)

        except pyodbc.Error as ex:
            print(f"[数据库] 检查/创建表结构时出错: {ex}")

        # 确保 messages.content 字段支持长文本
        try:
            content_column = None
            try:
                for col in self.cursor.columns(table='messages'):
                    if col.column_name and col.column_name.lower() == 'content':
                        content_column = col
                        break
            except pyodbc.Error as ex:
                print(f"[数据库] 无法获取列信息: {ex}")

            if content_column:
                type_name = (content_column.type_name or '').upper()
                column_size = content_column.column_size
                print(f"[数据库检查] messages.content 类型: {type_name}({column_size if column_size else 'MAX'})")

                needs_upgrade = False
                if type_name in {'VARCHAR', 'NVARCHAR', 'CHAR', 'NCHAR', 'VARWCHAR', 'LONGVARCHAR', 'TEXT'}:
                    if column_size is None:
                        # TEXT 但大小未知，保守处理：Access 的 LONGTEXT 会返回 None，此时无需升级
                        needs_upgrade = type_name not in {'TEXT'} or ('ACCESS' not in upper_dbms)
                    else:
                        needs_upgrade = column_size < 2000
                elif type_name in {'MEMO', 'LONGTEXT', 'NTEXT'}:
                    needs_upgrade = False
                else:
                    needs_upgrade = True

                if needs_upgrade:
                    if 'ACCESS' in upper_dbms:
                        alter_sql = 'ALTER TABLE messages ALTER COLUMN content LONGTEXT'
                    elif 'MYSQL' in upper_dbms:
                        alter_sql = 'ALTER TABLE messages MODIFY content LONGTEXT'
                    elif 'SQL SERVER' in upper_dbms or 'MICROSOFT SQL SERVER' in upper_dbms:
                        alter_sql = 'ALTER TABLE messages ALTER COLUMN content NVARCHAR(MAX)'
                    elif 'POSTGRE' in upper_dbms:
                        alter_sql = 'ALTER TABLE messages ALTER COLUMN content TYPE TEXT'
                    else:
                        alter_sql = 'ALTER TABLE messages ALTER COLUMN content TEXT'

                    print(f"⚠️ content 字段容量不足，正在执行: {alter_sql}")
                    try:
                        self.cursor.execute(alter_sql)
                        print("[OK] content 字段已升级为长文本类型")
                    except pyodbc.Error as ex:
                        print(f"❌ content 字段升级失败: {ex}")
                else:
                    print("[OK] content 字段类型符合要求")
            else:
                print("⚠️ 未找到 messages.content 列的信息")
        except Exception as ex:
            print(f"⚠️ 检查/升级 content 字段发生异常: {ex}")

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

    def add_message(self, conversation_id, role, content, file_paths=None):
        """添加消息到数据库
        
        Args:
            conversation_id: 对话ID
            role: 角色('user' 或 'assistant')
            content: 消息内容
            file_paths: 附件文件路径列表（可选）
        """
        import json
        
        # 将文件路径列表转换为JSON字符串
        files_json = json.dumps(file_paths, ensure_ascii=False) if file_paths else None
        
        self.cursor.execute(
            'INSERT INTO messages (conversation_id, role, content, files) VALUES (?, ?, ?, ?)', 
            (conversation_id, role, content, files_json)
        )
        self.conn.commit()

    def get_history(self, conversation_id):
        if not conversation_id:
            return []
        import json
        
        self.cursor.execute(
            'SELECT role, content, files FROM messages WHERE conversation_id = ? ORDER BY id ASC', 
            (conversation_id,)
        )
        
        messages = []
        for row in self.cursor.fetchall():
            message = {'role': row.role, 'content': row.content}
            # 【新增】解析附件信息
            if row.files:
                try:
                    message['files'] = json.loads(row.files)
                except:
                    pass
            messages.append(message)
        
        return messages

    def delete_messages_from_index(self, conversation_id, start_index):
        """删除从指定索引开始的所有消息（优化兼容性 - 两步法）"""
        try:
            # 步骤 1: 获取所有消息的 ID 列表（按插入顺序排序）
            self.cursor.execute(
                'SELECT id FROM messages WHERE conversation_id = ? ORDER BY id ASC', 
                (conversation_id,)
            )
            all_ids = [row[0] for row in self.cursor.fetchall()]
            
            # 检查索引是否有效
            if start_index >= len(all_ids):
                print(f"[数据库] 起始索引 {start_index} 超出消息总数 {len(all_ids)}，无需删除")
                return
            
            if start_index < 0:
                print(f"[数据库] 起始索引 {start_index} 无效（不能为负数）")
                return
            
            # 获取要删除的第一条消息的数据库 ID
            start_db_id = all_ids[start_index]
            
            print(f"[数据库] 准备删除对话 {conversation_id} 从索引 {start_index}（ID={start_db_id}）开始的 {len(all_ids) - start_index} 条消息")
            
            # 步骤 2: 删除 ID 大于等于该 ID 的所有消息
            self.cursor.execute(
                'DELETE FROM messages WHERE conversation_id = ? AND id >= ?',
                (conversation_id, start_db_id)
            )
            
            affected_rows = self.cursor.rowcount
            self.conn.commit()
            
            print(f"[数据库] ✅ 已删除 {affected_rows} 条消息（从索引 {start_index} 开始）")
            
        except Exception as e:
            print(f"[数据库] ❌ 删除消息失败: {e}")
            import traceback
            traceback.print_exc()
            self.conn.rollback()

    def delete_message_by_index(self, conversation_id, message_index):
        """删除指定索引的单条消息（优化兼容性 - 两步法）"""
        try:
            print(f"[数据库] 删除消息: 对话ID={conversation_id}, 索引={message_index}")
            
            # 步骤 1: 获取所有消息的 ID 列表（按插入顺序排序）
            self.cursor.execute(
                'SELECT id FROM messages WHERE conversation_id = ? ORDER BY id ASC', 
                (conversation_id,)
            )
            all_ids = [row[0] for row in self.cursor.fetchall()]
            
            print(f"[数据库] 删除前消息总数: {len(all_ids)}")
            
            # 检查索引是否有效
            if message_index >= len(all_ids) or message_index < 0:
                print(f"[数据库] ❌ 索引 {message_index} 无效，消息总数 {len(all_ids)}")
                return
            
            # 获取要删除的消息的数据库 ID
            db_id_to_delete = all_ids[message_index]
            
            print(f"[数据库] 准备删除消息 ID={db_id_to_delete}（索引={message_index}）")
            
            # 步骤 2: 根据唯一 ID 进行删除
            self.cursor.execute('DELETE FROM messages WHERE id = ?', (db_id_to_delete,))
            
            affected_rows = self.cursor.rowcount
            self.conn.commit()
            
            print(f"[数据库] 删除操作影响行数: {affected_rows}")
            
            if affected_rows > 0:
                print(f"[数据库] ✅ 消息（索引 {message_index}）已成功删除")
            else:
                print(f"[数据库] ⚠️ 消息（ID {db_id_to_delete}）删除失败，未影响任何行")
            
        except Exception as e:
            print(f"[数据库] ❌ 删除单条消息失败: {e}")
            import traceback
            traceback.print_exc()
            self.conn.rollback()

    def close(self):
        self.conn.close()