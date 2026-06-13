# 数据库配置 (SQLite - 零安装)
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dine_in.db')
SECRET_KEY = os.getenv("SECRET_KEY", "dine-in-v2-dev-key-change-in-production")

# LLM 配置 (DeepSeek)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")
LLM_BASE_URL = "https://api.deepseek.com"
