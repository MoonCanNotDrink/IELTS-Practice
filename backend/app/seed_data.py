"""Seed the database with IELTS speaking topics and writing prompts."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.cambridge_writing_prompts import CAMBRIDGE_ACADEMIC_WRITING_PROMPTS
from app.models import Topic, WritingPrompt

SEED_TOPICS = [
    # ─── Places ───────────────────────────────────────────────
    {
        "title": "Describe a place you visited that was very crowded",
        "points": ["Where the place was", "When you went there", "Why it was crowded",
                   "And explain how you felt about being there"],
        "category": "places"
    },
    {
        "title": "Describe a city you would like to visit in the future",
        "points": ["Where the city is", "How you learned about it", "What you would like to do there",
                   "And explain why you want to visit this city"],
        "category": "places"
    },
    {
        "title": "Describe a public place that you think needs improvement",
        "points": ["What the place is", "Where it is located", "What problems it has",
                   "And explain what improvements should be made"],
        "category": "places"
    },
    {
        "title": "Describe a natural place you have visited and enjoyed",
        "points": ["Where it was", "Who you went with", "What you saw and did there",
                   "And explain why you enjoyed it"],
        "category": "places"
    },
    {
        "title": "Describe a building you find interesting",
        "points": ["What the building is and where it is", "What it is used for",
                   "Why you find it interesting",
                   "And explain what you think makes it special"],
        "category": "places"
    },

    # ─── People ───────────────────────────────────────────────
    {
        "title": "Describe a person who has influenced you a lot",
        "points": ["Who this person is", "How you know this person",
                   "What this person has done to influence you",
                   "And explain why this person has had such a big influence on you"],
        "category": "people"
    },
    {
        "title": "Describe a friend you enjoy spending time with",
        "points": ["Who this friend is", "How you met this person",
                   "What you usually do together",
                   "And explain why you enjoy spending time with them"],
        "category": "people"
    },
    {
        "title": "Describe a famous person you admire",
        "points": ["Who this person is", "What they are famous for",
                   "How you first heard about them",
                   "And explain why you admire them"],
        "category": "people"
    },
    {
        "title": "Describe a person in your family who you most admire",
        "points": ["Who this person is", "What this person does",
                   "What they have achieved",
                   "And explain why you admire them"],
        "category": "people"
    },

    # ─── Experiences ──────────────────────────────────────────
    {
        "title": "Describe a time when you helped someone",
        "points": ["Who you helped", "What the situation was", "How you helped them",
                   "And explain how you felt about helping this person"],
        "category": "experiences"
    },
    {
        "title": "Describe a skill that took you a long time to learn",
        "points": ["What the skill was", "When you started learning it",
                   "Why it took you a long time",
                   "And explain how you felt when you finally learned it"],
        "category": "experiences"
    },
    {
        "title": "Describe an important decision you made",
        "points": ["What the decision was", "When you made it", "How you made the decision",
                   "And explain why it was important"],
        "category": "experiences"
    },
    {
        "title": "Describe a time you received good news",
        "points": ["What the news was", "When and where you received it", "Who told you the news",
                   "And explain why it was good news for you"],
        "category": "experiences"
    },
    {
        "title": "Describe an achievement you are proud of",
        "points": ["What you achieved", "When it happened", "How you achieved it",
                   "And explain why you are proud of this achievement"],
        "category": "experiences"
    },
    {
        "title": "Describe a time you had to wait for something important",
        "points": ["What you were waiting for", "Where and how long you waited",
                   "Why you had to wait",
                   "And explain how you felt while waiting"],
        "category": "experiences"
    },
    {
        "title": "Describe a time you made a mistake and learned from it",
        "points": ["What the mistake was", "When it happened",
                   "What you did to fix it",
                   "And explain what you learned from this experience"],
        "category": "experiences"
    },
    {
        "title": "Describe an occasion when you had to do something in a hurry",
        "points": ["What you had to do", "Why you were in a hurry",
                   "How successfully you completed it",
                   "And explain how you felt during this experience"],
        "category": "experiences"
    },

    # ─── Objects ──────────────────────────────────────────────
    {
        "title": "Describe a piece of technology that you find useful",
        "points": ["What it is", "How often you use it", "What you use it for",
                   "And explain why you find it useful"],
        "category": "objects"
    },
    {
        "title": "Describe a book that you have recently read",
        "points": ["What the book was about", "Why you decided to read it",
                   "What you liked or disliked about it",
                   "And explain whether you would recommend it to others"],
        "category": "objects"
    },
    {
        "title": "Describe a gift you gave or received that was memorable",
        "points": ["What the gift was", "Who gave it or who you gave it to",
                   "When this happened",
                   "And explain why it was memorable"],
        "category": "objects"
    },
    {
        "title": "Describe a piece of clothing or jewellery that you wear on special occasions",
        "points": ["What it is", "Where you got it from", "When you wear it",
                   "And explain why it is special to you"],
        "category": "objects"
    },

    # ─── Culture & Society ────────────────────────────────────
    {
        "title": "Describe a tradition in your country that you enjoy",
        "points": ["What the tradition is", "When it takes place",
                   "What you do during this tradition",
                   "And explain why you enjoy it"],
        "category": "culture"
    },
    {
        "title": "Describe a festival or celebration you enjoy",
        "points": ["What the festival or celebration is", "When it takes place",
                   "How you celebrate it",
                   "And explain why you enjoy it"],
        "category": "culture"
    },
    {
        "title": "Describe a local food or dish you like",
        "points": ["What the food or dish is", "How it is made",
                   "When you eat it",
                   "And explain why you like it"],
        "category": "culture"
    },

    # ─── Media & Education ────────────────────────────────────
    {
        "title": "Describe a movie that made a strong impression on you",
        "points": ["What the movie was", "When you watched it", "What it was about",
                   "And explain why it made a strong impression on you"],
        "category": "media"
    },
    {
        "title": "Describe a TV program or online video you enjoy watching",
        "points": ["What it is called and what type of program it is",
                   "What it is about",
                   "Who makes it",
                   "And explain why you enjoy watching it"],
        "category": "media"
    },
    {
        "title": "Describe a subject you enjoyed studying at school",
        "points": ["What the subject was", "Who taught it", "What you learned in this subject",
                   "And explain why you enjoyed studying it"],
        "category": "education"
    },
    {
        "title": "Describe a course or class you have taken outside of school",
        "points": ["What the course was", "Why you decided to take it",
                   "What you learned",
                   "And explain whether you would recommend it to others"],
        "category": "education"
    },
    {
        "title": "Describe a time you taught someone something",
        "points": ["Who you taught", "What you taught them",
                   "How you taught them",
                   "And explain how successful you were in teaching them"],
        "category": "education"
    },
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
    """Insert seed topics if the topics table is empty."""
    result = await db.execute(select(Topic).limit(1))
    if result.scalars().first() is not None:
        return  # Already seeded

    for topic_data in SEED_TOPICS:
        topic = Topic(**topic_data)
        db.add(topic)

    await db.commit()
    print(f"✅ Seeded {len(SEED_TOPICS)} topics into the database.")


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
