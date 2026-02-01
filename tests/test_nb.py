import asyncio
import sys

from notebooklm import NotebookLMClient


async def main():
    print(f"当前 Python 路径: {sys.executable}")

    # 尝试初始化客户端（注意：如果没有登录，这一步可能会报错，但在测试导入时是正常的）
    try:
        # from_storage() 会尝试从本地读取 Cookie，如果没有登录过会失败
        print("✅ 成功导入 NotebookLMClient！正在检查本地认证信息...")
        async with await NotebookLMClient.from_storage() as client:
            print("🎉 认证成功！客户端已就绪。")
            print(f"当前 Notebook 列表: {await client.notebooks.list()}")

    except FileNotFoundError:
        print("⚠️ 导入成功，但未找到认证信息。")
        print("请运行 'uv run notebooklm login' 进行首次登录。")
    except Exception as e:
        print(f"❌ 运行时错误 (这是正常的，如果还没配置Cookie): {e}")


if __name__ == "__main__":
    asyncio.run(main())
