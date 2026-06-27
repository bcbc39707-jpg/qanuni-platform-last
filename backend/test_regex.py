import re
from app.db.session import AsyncSessionLocal
from app.models.law import Law
from sqlalchemy import select
import asyncio

async def test():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Law).where(Law.category == 'دستور'))
        law = result.scalar_one_or_none()
        if law and law.full_text:
            ft_articles = []
            patterns = [
                r'المادة\s*\(?(\d+)\)?:?',
                r'(\d+)\s*\(مادة\s*\)?:?\s*',
                r'مادة\s*\(?(\d+)\)?:?',
            ]
            parts = []
            active_pat = None
            for pat in patterns:
                parts = re.split(pat, law.full_text)
                if len(parts) > 1:
                    active_pat = pat
                    break

            if len(parts) > 1:
                for i in range(1, len(parts), 2):
                    art_num = parts[i]
                    art_text = parts[i+1].strip() if i+1 < len(parts) else ''
                    ft_articles.append((art_num, len(art_text)))

            print('Full text length:', len(law.full_text))
            print('ft_articles count:', len(ft_articles))
            if ft_articles:
                nums = [a[0] for a in ft_articles]
                print('Pattern used:', active_pat)
                print('First 5 nums:', nums[:5])
                print('Last 5 nums:', nums[-5:])
                int_nums = sorted([int(n) for n in nums if n.isdigit()])
                if int_nums:
                    print('Min num:', int_nums[0])
                    print('Max num:', int_nums[-1])
                    expected = list(range(1, int_nums[-1] + 1))
                    missing = [str(i) for i in expected if str(i) not in nums]
                    print('Missing count:', len(missing))
                    if missing:
                        print('First 10 missing:', missing[:10])

asyncio.run(test())
