from pymongo import MongoClient
from config import MONGO_URI

# 初始化 MongoDB 连接
client = MongoClient(MONGO_URI)

# 打印数据库连接是否成功
try:
    # 尝试获取数据库信息
    client.admin.command('ping')
    print("MongoDB connected successfully!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# 选择数据库
db = client['tennis_team']  # 选择 tennis_team 数据库

# 选择集合
posts = db['posts']  # 存储动态的集合
bookings = db['bookings']  # 存储预定信息的集合
