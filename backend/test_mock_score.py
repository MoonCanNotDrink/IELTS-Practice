import asyncio
from app.services.scoring_service import score_speaking

async def test():
    transcript = "Uh, yes, I think the internet is very important. I use it every day to read news and watch videos. But sometimes it is bad because people waste too much time on it. For example, my brother plays games all day. So it has good and bad sides."
    question = "Do you think the internet is good or bad?"
    
    print("Testing score_speaking...")
    res = await score_speaking(transcript, question, "part1", None)
    print("Result keys:", res.keys())
    print("Scores:", res.get('overall_score'), res.get('fluency_score'))
    print("Feedback length:", len(res.get('overall_feedback', '')))
    if "error" in res:
        print("Error:", res['error'])
        if 'detail' in res:
            print("Detail:", res['detail'])

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Force the model to test
    import os
    os.environ["GEMINI_MODEL"] = "gemini-2.0-flash"
    
    asyncio.run(test())
