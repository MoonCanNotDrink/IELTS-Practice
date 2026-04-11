"""Seed the database with IELTS speaking topics and writing prompts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cambridge_writing_prompts import CAMBRIDGE_ACADEMIC_WRITING_PROMPTS
from app.models import PracticeSession, Topic, WritingPrompt

CURRENT_PART2_SEASON = "2026-Q1"
LEGACY_PART2_SEASON = f"{CURRENT_PART2_SEASON}-legacy"


def _topic(title: str, points: list[str], category: str) -> dict:
    return {
        "title": title,
        "points": points,
        "category": category,
        "season": CURRENT_PART2_SEASON,
    }


SEED_TOPICS = [
    _topic(
        "Describe a famous person you would like to meet.",
        [
            "Who he/she is",
            "How you knew him/her",
            "How/where you would like to meet him/her",
            "And explain why you would like to meet him/her",
        ],
        "people",
    ),
    _topic(
        "Describe a child you know who likes drawing very much.",
        [
            "How you knew him/her",
            "What he/she is like",
            "How often he/she draws",
            "And explain why you think he/she likes drawing",
        ],
        "people",
    ),
    _topic(
        "Describe a person who makes plans a lot.",
        [
            "Who he/she is",
            "How you knew him/her",
            "What plans he/she makes",
            "And explain how you feel about this person",
        ],
        "people",
    ),
    _topic(
        "Describe a person who encouraged you to protect the nature.",
        [
            "Who he/she is",
            "How he/she encouraged you",
            "What he/she encouraged you to do",
            "And explain how you feel about this person",
        ],
        "people",
    ),
    _topic(
        "Describe a person who gave a clever solution to a problem.",
        [
            "Who the person is",
            "When you met this person",
            "What the problem was",
            "And explain why you think it was a clever solution",
        ],
        "people",
    ),
    _topic(
        "Describe one of your friends who learned a skill from someone (not a teacher).",
        [
            "Who he/she is",
            "What skill he/she learned",
            "How he/she learned",
            "And explain whether it would be easier to learn from a teacher",
        ],
        "people",
    ),
    _topic(
        "Describe someone living in your area who often helps others.",
        [
            "What he/she is like",
            "How he/she helps others",
            "Why his/her help is beneficial",
            "And explain why he/she often helps others",
        ],
        "people",
    ),
    _topic(
        "Describe a friend of yours who is good at music/singing.",
        [
            "Who he/she is",
            "When/Where you listen to his/her music/singing",
            "What kind of music/songs he/she is good at",
            "And explain how you feel when listening to his music/singing",
        ],
        "people",
    ),
    _topic(
        "Describe a good friend who is important to you.",
        [
            "Who he/she is",
            "How/Where you got to know him/her",
            "How long you have known each other",
            "And explain why he/she is important to you",
        ],
        "people",
    ),
    _topic(
        "Describe a person you know who runs a family business.",
        [
            "Who he/she is",
            "What the business is",
            "What products it sells",
            "And explain what you have learned from him/her",
        ],
        "people",
    ),
    _topic(
        "Describe a friend of yours who has a good habit.",
        [
            "Who he/she is",
            "What good habit he/she has",
            "When/how you noticed the good habit",
            "And explain how you will develop the same habit",
        ],
        "people",
    ),
    _topic(
        "Describe a creative person whose work you admire.",
        [
            "Who he/she is",
            "How you knew him/her",
            "What creative things he/she has done",
            "And explain why you think he/she is creative",
        ],
        "people",
    ),
    _topic(
        "Describe a popular person.",
        [
            "Who he/she is",
            "What he/she has done",
            "Why he/she is popular",
            "And explain how you feel about him/her",
        ],
        "people",
    ),
    _topic(
        "Describe something you cannot live without (not a computer/phone).",
        [
            "What it is",
            "What you do with it",
            "How it helps you in your life",
            "And explain why you cannot live without it",
        ],
        "objects",
    ),
    _topic(
        "Describe a piece of technology (not a phone) that you would like to own.",
        [
            "What it is",
            "How much it costs",
            "What you will use it for",
            "And explain why you would like to own it",
        ],
        "objects",
    ),
    _topic(
        "Describe an item on which you spent more than expected.",
        [
            "What it is",
            "How much you spent on it",
            "Why you bought it",
            "And explain why you think you spent more than expected",
        ],
        "objects",
    ),
    _topic(
        "Describe a wild animal that you want to know more about.",
        [
            "What it is",
            "When you saw it",
            "Where you saw it",
            "And explain why you want to know more about it",
        ],
        "objects",
    ),
    _topic(
        "Describe something important that your family has kept for a long time.",
        [
            "What it is",
            "What it is used for",
            "How your family got it",
            "And explain why it is important to your family",
        ],
        "objects",
    ),
    _topic(
        "Describe a book you read that you found useful.",
        [
            "What it is",
            "When and where you read it",
            "Why you think it is useful",
            "And explain how you feel about this book",
        ],
        "objects",
    ),
    _topic(
        "Describe a toy you got in your childhood.",
        [
            "What it was",
            "When you got it",
            "How you got it",
            "And explain how you felt about it.",
        ],
        "objects",
    ),
    _topic(
        "Describe an invention that is useful in your daily life.",
        [
            "What the invention is",
            "What it can do",
            "How popular it is",
            "And explain whether it is difficult or easy to use",
        ],
        "objects",
    ),
    _topic(
        "Describe a perfect job you want to do in the future.",
        [
            "What it is",
            "How you can find this job",
            "What you need to prepare for this job",
            "And explain why you want to do this job",
        ],
        "general",
    ),
    _topic(
        "Describe a program or app on your computer or phone.",
        [
            "What it is",
            "When/how you use it",
            "Where you found it",
            "And explain how you feel about it",
        ],
        "general",
    ),
    _topic(
        "Describe a movie you watched recently.",
        [
            "When and where you watched it",
            "Who you watched it with",
            "What it was about",
            "And explain why you chose to watch this movie",
        ],
        "general",
    ),
    _topic(
        "Describe a natural talent you want to improve.",
        [
            "What it is",
            "When you discovered it",
            "How you want to improve it",
            "And explain how you feel about it",
        ],
        "general",
    ),
    _topic(
        "Describe an interesting traditional story.",
        [
            "What the story is about",
            "When/how you know it",
            "Who told you the story",
            "And explain how you felt when you first heard it",
        ],
        "general",
    ),
    _topic(
        "Describe one area of science (medicine, physics and etc.) that sounds interesting to you.",
        [
            "What it is",
            "When you knew it",
            "How you knew it",
            "And explain why it sounds interesting to you",
        ],
        "general",
    ),
    _topic(
        "Describe a water sport you would like to try in the future.",
        [
            "What it is",
            "What you need to do this sport",
            "Why you want to learn this sport",
            "And explain whether it is difficult or easy to learn this sport",
        ],
        "general",
    ),
    _topic(
        "Describe your favourite place in your home where you can relax.",
        [
            "Where it is",
            "What it is like",
            "What you enjoy doing there",
            "And explain why you feel relaxed at this place",
        ],
        "places",
    ),
    _topic(
        "Describe a shopping mall.",
        [
            "What its name is",
            "Where it is",
            "How often you visit it",
            "And what you usually buy at the mall",
        ],
        "places",
    ),
    _topic(
        "Describe a place with a lot of trees that you would like to visit (e.g. a forest, oasis).",
        [
            "Where it is",
            "How you knew this place",
            "What it is like",
            "And explain why you would like to visit it",
        ],
        "places",
    ),
    _topic(
        "Describe an interesting building you saw during a trip.",
        [
            "Where you saw it",
            "What it looks like",
            "What you have known about it",
            "And explain why you think it is interesting",
        ],
        "places",
    ),
    _topic(
        "Describe a natural place (e.g. parks, mountains).",
        [
            "Where this place is",
            "How you knew this place",
            "What it is like",
        ],
        "places",
    ),
    _topic(
        "Describe a time when you felt proud of a family member.",
        [
            "When it happened",
            "Who the person is",
            "What the person did",
            "And explain why you felt proud of him/her",
        ],
        "experiences",
    ),
    _topic(
        "Describe an occasion when you were not allowed to use a mobile phone.",
        [
            "When it was",
            "Where you were",
            "Why you were not allowed to use it",
            "And explain how you felt about that",
        ],
        "experiences",
    ),
    _topic(
        "Describe an occasion when many people were smiling.",
        [
            "When it happened",
            "Who you were with",
            "What happened",
            "And explain why many people were smiling",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you gave advice to others.",
        [
            "When it was",
            "To whom you gave the advice",
            "What the advice was",
            "And explain why you gave the advice",
        ],
        "experiences",
    ),
    _topic(
        "Describe a bicycle/motorcycle/car trip you would like to go on.",
        [
            "Who you would like to go with",
            "Where you would like to go",
            "When you would like to go",
            "And explain why you would like to go by bicycle/motorcycle/car",
        ],
        "experiences",
    ),
    _topic(
        "Describe a music event that you didn't enjoy.",
        [
            "What it was",
            "Who you went with",
            "Why you decided to go there",
            "And explain why you didn't enjoy it",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you used imagination.",
        [
            "When this happened",
            "Why you need to use imagination",
            "How you used your imagination",
            "And explain how you felt about this experience",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you encouraged someone to do something that he/she didn't want to do.",
        [
            "Who he or she is",
            "What you encouraged him/her to do",
            "How he/she reacted",
            "And explain why you encouraged him/her to do it",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you told an important truth to your friend.",
        [
            "When it happened",
            "Who this friend is",
            "What kind of truth you told him or her",
            "And explain what reactions he or she had then",
        ],
        "experiences",
    ),
    _topic(
        "Describe an occasion when you lost your way.",
        [
            "Where you were",
            "What happened",
            "How you felt about it",
            "And explain how you found your way",
        ],
        "experiences",
    ),
    _topic(
        "Describe a trip you would like to make again.",
        [
            "Where and when you went",
            "Who you made the trip with",
            "What you did during the trip",
            "And explain why you would like to make a trip again",
        ],
        "experiences",
    ),
    _topic(
        "Describe a dinner that you really enjoyed.",
        [
            "When it was",
            "What you ate at the dinner",
            "Who you had dinner with",
            "And explain why you enjoyed the dinner",
        ],
        "experiences",
    ),
    _topic(
        "Describe a long journey you had.",
        [
            "Where you went",
            "Who you had the journey with",
            "Why you had the journey",
            "And explain how you felt about the journey",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when the electricity suddenly went off.",
        [
            "When/where it happened",
            "How long it lasted",
            "What you did during that time",
            "And explain how you felt about it",
        ],
        "experiences",
    ),
    _topic(
        "Describe an exciting activity you have tried for the first time.",
        [
            "What it is",
            "When/where you did it",
            "Why you thought it was exciting",
            "And explain how you felt about it",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you first talked to others in a foreign language.",
        [
            "When this happened",
            "Who you talked to",
            "What you talked about",
            "And explain how you felt about this experience",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you saw something interesting on social media.",
        [
            "When it was",
            "Where you saw it",
            "What you saw",
            "And explain why you think it was interesting",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you broke something.",
        [
            "What it was",
            "When/where that happened",
            "How you broke it",
            "And explain what you did after that",
        ],
        "experiences",
    ),
    _topic(
        "Describe an important decision you made with the help of others.",
        [
            "Who helped you make it",
            "What the decision was",
            "When it happened",
            "And explain how you felt about it",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you waited for something special to happen.",
        [
            "What you waited for",
            "Where you waited",
            "Why it was special",
            "And explain how you felt while you were waiting",
        ],
        "experiences",
    ),
    _topic(
        "Describe a talk you gave to a group of people.",
        [
            "Who you gave the talk to",
            "What the talk was about",
            "Why you gave the talk",
            "And explain how you felt about the talk",
        ],
        "experiences",
    ),
    _topic(
        "Describe a positive change you made in your life.",
        [
            "What the change was",
            "When it happened",
            "How it happened",
            "And explain why it was a positive change",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you received good service in a shop/store.",
        [
            "Where the shop is",
            "When you went to the shop",
            "What service you received from the staff",
            "And explain how you felt about the service",
        ],
        "experiences",
    ),
    _topic(
        "Describe an experience when someone apologized to you.",
        [
            "When it happened",
            "Who he or she was",
            "Why he or she apologized to you",
            "And explain how you felt about it",
        ],
        "experiences",
    ),
    _topic(
        "Describe a time when you had an unusual meal.",
        [
            "When you had it",
            "Where you had it",
            "Who you had the meal with",
            "And explain why it was unusual",
        ],
        "experiences",
    ),
]


DEFAULT_WRITING_PROMPTS = [
    {
        "slug": "task1-library-visits-bar-chart",
        "task_type": "task1",
        "title": "Task 1 · Library visits by age group",
        "prompt_text": "The bar chart below shows the number of weekly visits to a city library by four age groups in 2024. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
        "prompt_details": {
            "format": "bar_chart",
            "notes": [
                "Age groups: children, teenagers, adults, seniors",
                "Focus on the highest and lowest visiting groups",
                "Include one or two clear comparisons"
            ],
            "chart_data": {
                "type": "bar",
                "data": {
                    "labels": ["Children (5-12)", "Teenagers (13-18)", "Adults (19-64)", "Seniors (65+)"],
                    "datasets": [
                        {
                            "label": "Weekly visits",
                            "data": [420, 180, 650, 310],
                            "backgroundColor": [
                                "rgba(54, 162, 235, 0.7)",
                                "rgba(255, 159, 64, 0.7)",
                                "rgba(75, 192, 192, 0.7)",
                                "rgba(153, 102, 255, 0.7)"
                            ],
                            "borderColor": [
                                "rgba(54, 162, 235, 1)",
                                "rgba(255, 159, 64, 1)",
                                "rgba(75, 192, 192, 1)",
                                "rgba(153, 102, 255, 1)"
                            ],
                            "borderWidth": 1
                        }
                    ]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {"display": True, "text": "Weekly Library Visits by Age Group (2024)"},
                        "legend": {"display": False}
                    },
                    "scales": {
                        "y": {"beginAtZero": True, "title": {"display": True, "text": "Number of visits"}}
                    }
                }
            }
        },
    },
    {
        "slug": "task1-student-housing-pie-chart",
        "task_type": "task1",
        "title": "Task 1 · Student housing spending",
        "prompt_text": "The pie charts below show how university students in one country spent their monthly housing budget in 2010 and 2025. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
        "prompt_details": {
            "format": "pie_chart",
            "notes": [
                "Compare the two years directly",
                "Highlight the categories that rose or fell the most",
                "Do not explain reasons that are not shown"
            ],
            "chart_data": {
                "type": "pie",
                "multi": True,
                "charts": [
                    {
                        "title": "2010",
                        "data": {
                            "labels": ["Rent", "Utilities", "Insurance", "Maintenance", "Other"],
                            "datasets": [{
                                "data": [55, 15, 10, 12, 8],
                                "backgroundColor": [
                                    "rgba(255, 99, 132, 0.7)",
                                    "rgba(54, 162, 235, 0.7)",
                                    "rgba(255, 206, 86, 0.7)",
                                    "rgba(75, 192, 192, 0.7)",
                                    "rgba(153, 102, 255, 0.7)"
                                ]
                            }]
                        }
                    },
                    {
                        "title": "2025",
                        "data": {
                            "labels": ["Rent", "Utilities", "Insurance", "Maintenance", "Other"],
                            "datasets": [{
                                "data": [62, 13, 8, 9, 8],
                                "backgroundColor": [
                                    "rgba(255, 99, 132, 0.7)",
                                    "rgba(54, 162, 235, 0.7)",
                                    "rgba(255, 206, 86, 0.7)",
                                    "rgba(75, 192, 192, 0.7)",
                                    "rgba(153, 102, 255, 0.7)"
                                ]
                            }]
                        }
                    }
                ]
            }
        },
    },
    {
        "slug": "task1-electricity-production-line-graph",
        "task_type": "task1",
        "title": "Task 1 · Electricity production by source",
        "prompt_text": "The line graph below shows electricity production (in terawatt-hours) in a European country from three different energy sources between 1980 and 2020. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
        "prompt_details": {
            "format": "line_graph",
            "notes": [
                "Identify overall trends for each energy source",
                "Note any crossover points where one source overtook another",
                "Mention the starting and ending values"
            ],
            "chart_data": {
                "type": "line",
                "data": {
                    "labels": ["1980", "1985", "1990", "1995", "2000", "2005", "2010", "2015", "2020"],
                    "datasets": [
                        {
                            "label": "Nuclear",
                            "data": [30, 55, 90, 130, 155, 170, 180, 190, 200],
                            "borderColor": "rgba(75, 192, 192, 1)",
                            "backgroundColor": "rgba(75, 192, 192, 0.1)",
                            "fill": False,
                            "tension": 0.3
                        },
                        {
                            "label": "Natural Gas",
                            "data": [80, 75, 68, 60, 55, 62, 70, 65, 50],
                            "borderColor": "rgba(255, 159, 64, 1)",
                            "backgroundColor": "rgba(255, 159, 64, 0.1)",
                            "fill": False,
                            "tension": 0.3
                        },
                        {
                            "label": "Renewables",
                            "data": [5, 8, 12, 18, 25, 40, 65, 95, 140],
                            "borderColor": "rgba(54, 162, 235, 1)",
                            "backgroundColor": "rgba(54, 162, 235, 0.1)",
                            "fill": False,
                            "tension": 0.3
                        }
                    ]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {"display": True, "text": "Electricity Production by Source (1980–2020)"},
                        "legend": {"position": "top"}
                    },
                    "scales": {
                        "y": {"beginAtZero": True, "title": {"display": True, "text": "Terawatt-hours (TWh)"}},
                        "x": {"title": {"display": True, "text": "Year"}}
                    }
                }
            }
        },
    },
    {
        "slug": "task1-water-usage-table",
        "task_type": "task1",
        "title": "Task 1 · Water usage by sector",
        "prompt_text": "The table below shows the average daily water usage (in millions of litres) by four sectors in three Australian cities in 2023. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
        "prompt_details": {
            "format": "table",
            "notes": [
                "Compare sectors across the three cities",
                "Identify the largest and smallest consumers",
                "Note any significant differences between cities"
            ],
            "chart_data": {
                "type": "table",
                "title": "Average Daily Water Usage by Sector (millions of litres, 2023)",
                "headers": ["Sector", "Sydney", "Melbourne", "Brisbane"],
                "rows": [
                    ["Residential", "520", "410", "280"],
                    ["Industrial", "310", "260", "190"],
                    ["Agricultural", "180", "220", "340"],
                    ["Commercial", "140", "120", "95"]
                ]
            }
        },
    },
    {
        "slug": "task2-online-learning-discipline",
        "task_type": "task2",
        "title": "Task 2 · Online learning and self-discipline",
        "prompt_text": "Some people believe that online courses require more self-discipline than traditional classroom learning, so they are not suitable for everyone. To what extent do you agree or disagree?",
        "prompt_details": {
            "notes": [
                "Take a clear position",
                "Support your view with reasons and examples",
                "Write in an academic style"
            ]
        },
    },
    {
        "slug": "task2-public-transport-investment",
        "task_type": "task2",
        "title": "Task 2 · Public transport investment",
        "prompt_text": "Governments should spend more money on public transport than on building new roads. Discuss both views and give your own opinion.",
        "prompt_details": {
            "notes": [
                "Discuss both sides before giving your opinion",
                "Use a balanced paragraph structure",
                "Support the opinion with specific examples"
            ]
        },
    },
    {
        "slug": "task2-work-life-balance-shorter-week",
        "task_type": "task2",
        "title": "Task 2 · Shorter working week",
        "prompt_text": "Many companies are considering a four-day working week for employees. What are the advantages and disadvantages of this change?",
        "prompt_details": {
            "notes": [
                "Cover both benefits and drawbacks",
                "Use examples from work or daily life",
                "Keep the conclusion concise"
            ]
        },
    },
]


SEED_WRITING_PROMPTS = DEFAULT_WRITING_PROMPTS + CAMBRIDGE_ACADEMIC_WRITING_PROMPTS


async def seed_topics(db: AsyncSession):
    """Sync the current official Part 2 topic bank without breaking history."""
    result = await db.execute(select(Topic).where(Topic.season == CURRENT_PART2_SEASON))
    existing_topics = result.scalars().all()
    existing_by_title = {topic.title: topic for topic in existing_topics}

    inserted = 0
    updated = 0
    deleted = 0
    preserved_legacy = 0

    for topic_data in SEED_TOPICS:
        existing = existing_by_title.pop(topic_data["title"], None)
        if existing is None:
            db.add(Topic(**topic_data))
            inserted += 1
            continue

        changed = False
        for field in ("points", "category", "season"):
            next_value = topic_data[field]
            if getattr(existing, field) != next_value:
                setattr(existing, field, next_value)
                changed = True

        if changed:
            updated += 1

    for obsolete_topic in existing_by_title.values():
        session_result = await db.execute(
            select(PracticeSession.id)
            .where(PracticeSession.topic_id == obsolete_topic.id)
            .limit(1)
        )
        if session_result.scalar_one_or_none() is None:
            await db.delete(obsolete_topic)
            deleted += 1
            continue

        obsolete_topic.season = LEGACY_PART2_SEASON
        preserved_legacy += 1

    if inserted or updated or deleted or preserved_legacy:
        await db.commit()
        print(
            "✅ Synced Part 2 topics into the database. "
            f"inserted={inserted}, updated={updated}, "
            f"deleted={deleted}, preserved_legacy={preserved_legacy}"
        )


async def seed_writing_prompts(db: AsyncSession):
    inserted = 0
    updated = 0
    result = await db.execute(select(WritingPrompt))
    existing_by_slug = {prompt.slug: prompt for prompt in result.scalars().all()}

    for prompt_data in SEED_WRITING_PROMPTS:
        existing = existing_by_slug.get(prompt_data["slug"])
        if existing is None:
            db.add(WritingPrompt(**prompt_data))
            inserted += 1
            continue

        changed = False
        for field in ("task_type", "title", "prompt_text", "prompt_details", "source"):
            next_value = prompt_data.get(field)
            if getattr(existing, field) != next_value:
                setattr(existing, field, next_value)
                changed = True

        if changed:
            updated += 1

    if inserted or updated:
        await db.commit()
        print(f"✅ Synced writing prompts into the database. inserted={inserted}, updated={updated}")
