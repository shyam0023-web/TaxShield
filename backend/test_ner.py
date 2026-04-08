import asyncio
from app.tools.notice_ner import NoticeNER

async def main():
    ner = NoticeNER()
    text = "Subject: Notice for Demand under section 73 of CGST Act. Financial Year: 2019-20. Total Demand: Rs 1000. \n\nPlease reply within 30 days."
    try:
        res = await ner.extract_entities(text)
        print("SUCCESS:", res)
    except Exception as e:
        print("ERROR:", e)
        print(type(e))

asyncio.run(main())
