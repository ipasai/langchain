import sqlite3
import asyncio
import js
from chat import call_llm

MOCK_DB_ANALYSIS = {
    "mysql": {
        "version": "MySQL 8.0.32 Community Server",
        "tables": [
            {"name": "users", "purpose": "使用者帳戶與登入憑證", "row_count": 1420, "columns": ["id(INT)", "email(VARCHAR)", "password_hash(VARCHAR)", "created_at(DATETIME)"], "relationships": []},
            {"name": "orders", "purpose": "電子商務訂單紀錄", "row_count": 865, "columns": ["id(INT)", "user_id(INT)", "total_amount(DECIMAL)", "status(VARCHAR)", "ordered_at(DATETIME)"], "relationships": ["user_id → users.id"]}
        ]
    },
    "postgres": {
        "version": "PostgreSQL 15.2 (Ubuntu 15.2-1.pgdg22.04+1)",
        "tables": [
            {"name": "employees", "purpose": "公司人事基礎資料", "row_count": 312, "columns": ["id(SERIAL)", "first_name(VARCHAR)", "last_name(VARCHAR)", "salary(NUMERIC)", "department_id(INT)"], "relationships": ["department_id → departments.id"]},
            {"name": "departments", "purpose": "部門組織劃分", "row_count": 8, "columns": ["id(SERIAL)", "name(VARCHAR)", "manager_id(INT)"], "relationships": []}
        ]
    }
}

def render_db_config_fields(event=None):
    db_type = js.document.getElementById("db-type-select").value
    container = js.document.getElementById("db-config-inputs")
    container.innerHTML = ""
    
    js.document.getElementById("db-analysis-card").style.display = "none"
    js.document.getElementById("db-ops-card").style.display = "none"
    js.document.getElementById("db-sql-generator-card").style.display = "none"

    if db_type == "sqlite":
        container.innerHTML = """
        <div style="grid-column: span 2;">
            <label class="section-label">SQLite 檔案路徑</label>
            <input type="text" id="db-sqlite-path" value="sample.db" placeholder="例如: sample.db">
        </div>
        """
    elif db_type in ["mysql", "postgres", "mariadb"]:
        port_defaults = {"mysql": "3306", "postgres": "5432", "mariadb": "3306"}
        container.innerHTML = f"""
        <div>
            <label class="section-label">主機 (Host)</label>
            <input type="text" id="db-host" value="localhost">
        </div>
        <div>
            <label class="section-label">連接埠 (Port)</label>
            <input type="text" id="db-port" value="{port_defaults[db_type]}">
        </div>
        <div>
            <label class="section-label">使用者</label>
            <input type="text" id="db-user" value="root">
        </div>
        <div>
            <label class="section-label">密碼</label>
            <input type="password" id="db-pass" placeholder="請輸入密碼">
        </div>
        <div style="grid-column: span 2;">
            <label class="section-label">資料庫名稱</label>
            <input type="text" id="db-database" placeholder="例如: test_db">
        </div>
        """
    elif db_type == "redis":
        container.innerHTML = """
        <div>
            <label class="section-label">主機 (Host)</label>
            <input type="text" id="db-host" value="localhost">
        </div>
        <div>
            <label class="section-label">連接埠 (Port)</label>
            <input type="text" id="db-port" value="6379">
        </div>
        <div>
            <label class="section-label">密碼 (Password)</label>
            <input type="password" id="db-pass" placeholder="請輸入密碼">
        </div>
        <div>
            <label class="section-label">Redis 資料庫索引</label>
            <input type="text" id="db-redis-index" value="0">
        </div>
        """
    elif db_type == "mongodb":
        container.innerHTML = """
        <div style="grid-column: span 2;">
            <label class="section-label">MongoDB 連線 URI</label>
            <input type="text" id="db-mongo-uri" value="mongodb://localhost:27017" placeholder="mongodb://username:password@host:port/database">
        </div>
        """

async def test_db_connection(event):
    db_type = js.document.getElementById("db-type-select").value
    status_msg = js.document.getElementById("db-connection-status-message")
    status_msg.innerHTML = '<div class="spinner-block"><div class="spinner-block-icon"></div> 正在連線測試中...</div>'
    
    await asyncio.sleep(0.5)
    
    analysis_card = js.document.getElementById("db-analysis-card")
    analysis_content = js.document.getElementById("db-analysis-content")
    ops_card = js.document.getElementById("db-ops-card")
    table_select = js.document.getElementById("db-table-select")
    sql_gen_card = js.document.getElementById("db-sql-generator-card")

    if db_type == "sqlite":
        filepath = js.document.getElementById("db-sqlite-path").value
        try:
            test_conn = sqlite3.connect(filepath)
            test_curr = test_conn.cursor()
            test_curr.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in test_curr.fetchall() if not row[0].startswith("sqlite_")]
            test_conn.close()
            
            status_msg.innerHTML = f'<div style="color:var(--color-emerald); font-weight:600; padding:10px 0;"><i class="fa-solid fa-circle-check"></i> 連線成功！成功連線至 SQLite 檔案: {filepath}</div>'
            analysis_card.style.display = "flex"
            
            html_analysis = f"""
            <div style="font-size:0.95rem; margin-bottom:15px;">
                <strong>資料庫類型:</strong> SQLite | <strong>核心版本:</strong> SQLite 3.39.5 (WebAssembly)
            </div>
            <div class="db-table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>資料表名稱</th>
                            <th>用途描述</th>
                            <th>欄位結構</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for t_name in tables:
                tc = sqlite3.connect(filepath)
                tcur = tc.cursor()
                tcur.execute(f"PRAGMA table_info({t_name})")
                columns = [f"{col[1]} ({col[2]})" for col in tcur.fetchall()]
                tc.close()
                purpose = "英文學習字庫紀錄" if t_name == "english_practice" else "歷史測驗記錄" if t_name == "study_sessions" else "應用系統表"
                html_analysis += f"""
                    <tr>
                        <td><strong>{t_name}</strong></td>
                        <td>{purpose}</td>
                        <td><code>{", ".join(columns)}</code></td>
                    </tr>
                """
            html_analysis += "</tbody></table></div>"
            analysis_content.innerHTML = html_analysis
            
            table_select.innerHTML = ""
            for t_name in tables:
                opt = js.document.createElement("option")
                opt.value = t_name
                opt.innerText = t_name
                table_select.appendChild(opt)
                
            ops_card.style.display = "flex"
            sql_gen_card.style.display = "flex"
            
        except Exception as e:
            status_msg.innerHTML = f'<div style="color:var(--color-crimson); font-weight:600; padding:10px 0;"><i class="fa-solid fa-circle-xmark"></i> 連線失敗: {str(e)}</div>'
            analysis_card.style.display = "none"
            ops_card.style.display = "none"
            sql_gen_card.style.display = "none"
    else:
        mock_key = "postgres" if db_type == "postgres" else "mysql"
        info = MOCK_DB_ANALYSIS.get(mock_key, MOCK_DB_ANALYSIS["mysql"])
        
        status_msg.innerHTML = f"""
        <div style="color:var(--color-emerald); font-weight:600; padding:10px 0; line-height:1.5;">
            <i class="fa-solid fa-circle-check"></i> 模擬連線成功！<br>
            <span style="font-size:0.85rem; font-weight:normal; color:var(--text-secondary);">
                註：瀏覽器沙盒已為您建立模擬連線結構，支持執行模擬 SQL 語法與 AI SQL 生成！
            </span>
        </div>
        """
        analysis_card.style.display = "flex"
        html_analysis = f"""
        <div style="font-size:0.95rem; margin-bottom:15px;">
            <strong>資料庫類型:</strong> {db_type.upper()} | <strong>伺服器版本:</strong> {info["version"]}
        </div>
        <div class="db-table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>資料表名稱</th>
                        <th>用途描述</th>
                        <th>資料行數</th>
                        <th>欄位結構</th>
                    </tr>
                </thead>
                <tbody>
        """
        for t in info["tables"]:
            html_analysis += f"""
                <tr>
                    <td><strong>{t["name"]}</strong></td>
                    <td>{t["purpose"]}</td>
                    <td>{t["row_count"]}</td>
                    <td><code>{", ".join(t["columns"])}</code></td>
                </tr>
            """
        html_analysis += "</tbody></table></div>"
        analysis_content.innerHTML = html_analysis
        
        table_select.innerHTML = ""
        for t in info["tables"]:
            opt = js.document.createElement("option")
            opt.value = t["name"]
            opt.innerText = t["name"]
            table_select.appendChild(opt)
            
        ops_card.style.display = "flex"
        sql_gen_card.style.display = "flex"

def preview_db_table(event):
    db_type = js.document.getElementById("db-type-select").value
    t_name = js.document.getElementById("db-table-select").value
    sql_input = js.document.getElementById("db-sql-query")
    sql_input.value = f"SELECT * FROM {t_name} LIMIT 10;"
    asyncio.ensure_future(run_custom_sql_query(None))

async def run_custom_sql_query(event):
    db_type = js.document.getElementById("db-type-select").value
    sql = js.document.getElementById("db-sql-query").value.strip()
    panel = js.document.getElementById("db-query-results-panel")
    container = js.document.getElementById("db-query-result-table-container")
    count_label = js.document.getElementById("db-query-result-count")
    del_select = js.document.getElementById("db-delete-row-select")
    
    if not sql:
        return
        
    panel.style.display = "flex"
    
    if db_type == "sqlite":
        filepath = js.document.getElementById("db-sqlite-path").value
        try:
            conn = sqlite3.connect(filepath)
            cursor = conn.cursor()
            cursor.execute(sql)
            
            if sql.lower().startswith("select"):
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description] if cursor.description else []
                conn.close()
                
                count_label.innerText = f"查詢成功：共找到 {len(rows)} 筆紀錄"
                
                html_table = "<table><thead><tr>"
                for c in cols:
                    html_table += f"<th>{c}</th>"
                html_table += "</tr></thead><tbody>"
                
                del_select.innerHTML = ""
                for idx, row in enumerate(rows):
                    html_table += "<tr>"
                    for val in row:
                        html_table += f"<td>{val}</td>"
                    html_table += "</tr>"
                    
                    row_id = row[0] if row else idx + 1
                    opt = js.document.createElement("option")
                    opt.value = str(row_id)
                    opt.innerText = f"ID: {row_id} | {row[1] if len(row)>1 else ''}"
                    del_select.appendChild(opt)
                    
                html_table += "</tbody></table>"
                container.innerHTML = html_table
            else:
                conn.commit()
                conn.close()
                count_label.innerText = "SQL 語句成功執行並寫入資料庫！"
                container.innerHTML = '<div style="color:var(--color-emerald); padding:15px; font-weight:600;">✅ 指令執行完成</div>'
        except Exception as e:
            count_label.innerText = "SQL 執行異常"
            container.innerHTML = f'<div style="color:var(--color-crimson); padding:15px; font-weight:600;">❌ 錯誤: {str(e)}</div>'
    else:
        count_label.innerText = "模擬遠端 SQL 查詢成功（回傳 2 筆數據）"
        container.innerHTML = """
        <table>
            <thead><tr><th>id</th><th>name</th><th>status</th></tr></thead>
            <tbody>
                <tr><td>1</td><td>Mock Entity Alpha</td><td>Active</td></tr>
                <tr><td>2</td><td>Mock Entity Beta</td><td>Pending</td></tr>
            </tbody>
        </table>
        """

def delete_sqlite_row(event, show_toast_fn):
    t_name = js.document.getElementById("db-table-select").value
    row_id = js.document.getElementById("db-delete-row-select").value
    filepath = js.document.getElementById("db-sqlite-path").value
    
    if not row_id or not t_name:
        show_toast_fn("請選擇要刪除的資料列", is_success=False)
        return
        
    try:
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {t_name} WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()
        show_toast_fn(f"成功刪除 {t_name} 中 ID 為 {row_id} 的資料！")
        asyncio.ensure_future(run_custom_sql_query(None))
    except Exception as e:
        show_toast_fn(f"刪除失敗: {e}", is_success=False)

async def generate_sql_from_natural_language(event):
    desc = js.document.getElementById("db-sql-desc").value.strip()
    if not desc:
        return
        
    db_type = js.document.getElementById("db-type-select").value
    gen_container = js.document.getElementById("db-generated-sql-container")
    code_block = js.document.getElementById("db-generated-sql-code")
    
    gen_container.style.display = "block"
    code_block.innerText = "AI 正在思考與生成 SQL 語句中，請稍候..."

    db_schema_details = ""
    if db_type == "sqlite":
        filepath = js.document.getElementById("db-sqlite-path").value
        tc = sqlite3.connect(filepath)
        cur = tc.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall() if not row[0].startswith("sqlite_")]
        for t_name in tables:
            cur.execute(f"PRAGMA table_info({t_name})")
            cols = [f"{c[1]}({c[2]})" for c in cur.fetchall()]
            db_schema_details += f"Table {t_name} columns: {', '.join(cols)}\n"
        tc.close()
    else:
        info = MOCK_DB_ANALYSIS.get(db_type, MOCK_DB_ANALYSIS["mysql"])
        for t in info["tables"]:
            db_schema_details += f"Table {t['name']} columns: {', '.join(t['columns'])}\n"

    prompt = f"""你是一個資料庫專家的 SQL 生成引擎。
目前資料庫類型為: {db_type.upper()}
資料庫結構說明如下：
{db_schema_details}

請根據使用者的中文敘述需求，寫出一個正確高效的 SQL 查詢。
需求敘述：{desc}

請僅輸出 SQL 語法本身，不要包含 any Markdown 標記或引言。"""

    provider = js.document.getElementById("ai-provider").value
    model = js.document.getElementById("ai-model").value
    temp = js.document.getElementById("ai-temp").value

    try:
        sql_response = await call_llm(provider, model, temp, "你是一位精通 SQL 的資料庫專家助手。", prompt)
        code_block.innerText = sql_response.strip()
    except Exception as e:
        code_block.innerText = f"生成失敗，錯誤訊息：{str(e)}"

def copy_generated_sql(event, show_toast_fn):
    code = js.document.getElementById("db-generated-sql-code").innerText.strip()
    js.navigator.clipboard.writeText(code)
    show_toast_fn("SQL 語法已複製到剪貼簿！")

def apply_generated_sql(event):
    code = js.document.getElementById("db-generated-sql-code").innerText.strip()
    js.document.getElementById("db-sql-query").value = code
    asyncio.ensure_future(run_custom_sql_query(None))

def export_query_results_csv(event, show_toast_fn):
    db_type = js.document.getElementById("db-type-select").value
    t_name = js.document.getElementById("db-table-select").value
    
    if db_type == "sqlite":
        filepath = js.document.getElementById("db-sqlite-path").value
        try:
            tc = sqlite3.connect(filepath)
            cur = tc.cursor()
            cur.execute(f"PRAGMA table_info({t_name})")
            columns = [col[1] for col in cur.fetchall()]
            cur.execute(f"SELECT * FROM {t_name}")
            rows = cur.fetchall()
            tc.close()
            
            csv_content = ",".join(columns) + "\n"
            for row in rows:
                csv_content += ",".join(f'"{str(v)}"' for v in row) + "\n"
                
            js.window.downloadFile(f"{t_name}_export.csv", csv_content, "text/csv")
            show_toast_fn("CSV 導出並下載成功")
        except Exception as e:
            show_toast_fn(f"CSV 導出失敗: {e}", is_success=False)
    else:
        show_toast_fn("模擬導出 CSV 成功", is_success=True)
        js.window.downloadFile("simulated_data.csv", "id,name,value\n1,模擬A,100\n2,模擬B,200", "text/csv")
