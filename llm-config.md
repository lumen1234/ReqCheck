

---

### `GET /api/config/llm` — 获取当前配置

**请求体：** 无

**响应：**
```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxx",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat"
}
```

---

### `PUT /api/config/llm` — 保存配置

**请求体：**
```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxx",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat"
}
```

**响应：**
```json
{
  "success": true
}
```

---

### `POST /api/config/llm/test` — 测试连接

**请求体：** 无（使用后端当前已存储的配置）

**响应（成功）：**
```json
{
  "ok": true,
  "model": "deepseek-chat",
  "reply": "Hello! How can I assist you today?"
}
```

**响应（失败）：**
```json
{
  "ok": false,
  "error": "Connection refused: invalid api_key or base_url"
}
```

