import asyncio
from tools import handle_github_inline_comment

async def main():
    res = await handle_github_inline_comment(
        file_path="App.jsx",
        action="read",
        source="github",
        github_repo="ArifRahaman/blog-website"
    )
    print(res)

asyncio.run(main())
