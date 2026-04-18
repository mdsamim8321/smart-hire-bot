import random

# Real Technical Questions templates and samples
REAL_QUESTIONS = [
    # Python
    {"question": "What is the correct way to create a function in Python?", "options": ["def function_name():", "create function_name():", "function function_name():", "void function_name():"], "correct": 0, "category": "Python", "difficulty": "Easy"},
    {"question": "Which data type is immutable in Python?", "options": ["List", "Dictionary", "Set", "Tuple"], "correct": 3, "category": "Python", "difficulty": "Medium"},
    {"question": "What does the 'self' keyword represent in a Python class?", "options": ["A global variable", "The instance of the class", "The parent class", "A reserved static keyword"], "correct": 1, "category": "Python", "difficulty": "Medium"},
    {"question": "How do you handle exceptions in Python?", "options": ["try-except", "catch-throw", "error-handle", "try-catch"], "correct": 0, "category": "Python", "difficulty": "Easy"},
    {"question": "What is a decorator in Python?", "options": ["A way to design UI", "A function that modifies another function", "A library for graphics", "A type of list comprehension"], "correct": 1, "category": "Python", "difficulty": "Hard"},
    
    # SQL
    {"question": "Which SQL statement is used to extract data from a database?", "options": ["GET", "EXTRACT", "SELECT", "OPEN"], "correct": 2, "category": "SQL", "difficulty": "Easy"},
    {"question": "What does CRUD stand for in database management?", "options": ["Create, Read, Update, Delete", "Copy, Remove, Undo, Do", "Create, Run, Upload, Deploy", "Create, Read, Undo, Delete"], "correct": 0, "category": "SQL", "difficulty": "Easy"},
    {"question": "Which keyword is used to sort the result-set in SQL?", "options": ["SORT BY", "ORDER BY", "GROUP BY", "ALIGN BY"], "correct": 1, "category": "SQL", "difficulty": "Medium"},
    {"question": "What is a PRIMARY KEY?", "options": ["A key that opens the database", "A unique identifier for a record", "The first column in any table", "A password for the database"], "correct": 1, "category": "SQL", "difficulty": "Easy"},
    {"question": "Which JOIN returns all records when there is a match in either left or right table?", "options": ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN"], "correct": 3, "category": "SQL", "difficulty": "Hard"},

    # DSA
    {"question": "What is the time complexity of a binary search?", "options": ["O(n)", "O(n^2)", "O(log n)", "O(1)"], "correct": 2, "category": "DSA", "difficulty": "Medium"},
    {"question": "Which data structure uses LIFO (Last In First Out)?", "options": ["Queue", "Stack", "Linked List", "Array"], "correct": 1, "category": "DSA", "difficulty": "Easy"},
    {"question": "What is the worst-case time complexity of Quick Sort?", "options": ["O(n log n)", "O(n)", "O(n^2)", "O(log n)"], "correct": 2, "category": "DSA", "difficulty": "Hard"},
    {"question": "A linked list is a ____ data structure.", "options": ["Linear", "Non-linear", "Hierarchical", "Circular"], "correct": 0, "category": "DSA", "difficulty": "Medium"},
    {"question": "Which algorithm is used to find the shortest path in a graph?", "options": ["Binary Search", "Dijkstra's Algorithm", "Merge Sort", "Bubble Sort"], "correct": 1, "category": "DSA", "difficulty": "Hard"},

    # Web Dev
    {"question": "What does CSS stand for?", "options": ["Creative Style Sheets", "Cascading Style Sheets", "Computer Style Sheets", "Colorful Style System"], "correct": 1, "category": "Web Dev", "difficulty": "Easy"},
    {"question": "Which HTML tag is used to define an internal style sheet?", "options": ["<css>", "<style>", "<script>", "<design>"], "correct": 1, "category": "Web Dev", "difficulty": "Easy"},
    {"question": "What is the purpose of 'use strict' in JavaScript?", "options": ["To speed up the code", "To enable strict mode for better error catching", "To import libraries", "To define variables"], "correct": 1, "category": "Web Dev", "difficulty": "Medium"},
    {"question": "Which company developed React?", "options": ["Google", "Twitter", "Facebook (Meta)", "Microsoft"], "correct": 2, "category": "Web Dev", "difficulty": "Easy"},
    {"question": "What does DOM stand for?", "options": ["Document Object Model", "Data Object Management", "Digital Orbit Model", "Document Online Method"], "correct": 0, "category": "Web Dev", "difficulty": "Medium"}
]

# Library of keywords to generate realistic variations
CONCEPTS = {
    "Python": ["List Comprehension", "Generators", "Asyncio", "Pandas", "Flask", "Django", "Pydantic", "Multi-threading"],
    "SQL": ["Indexing", "Normalization", "Stored Procedures", "Triggers", "Views", "ACID Properties", "Deadlocks", "Subqueries"],
    "DSA": ["Hash Tables", "Heaps", "Graphs", "Tries", "Dynamic Programming", "Recursion", "Backtracking", "AVL Trees"],
    "Web Dev": ["Redux", "TypeScript", "Flexbox", "Grid Layout", "REST API", "GraphQL", "JWT", "WebSockets"],
    "General Tech": ["Docker", "Kubernetes", "AWS", "Git", "CI/CD", "Agile", "Scrum", "DevOps"]
}

def generate_mcq_dataset(count=500):
    dataset = list(REAL_QUESTIONS)
    categories = list(CONCEPTS.keys())
    
    # Generate remaining questions
    while len(dataset) < count:
        cat = random.choice(categories)
        concept = random.choice(CONCEPTS[cat])
        diff = random.choice(["Easy", "Medium", "Hard"])
        
        # Template questions for realistic feel
        templates = [
            {
                "question": f"In the context of {cat}, what is the main purpose of {concept}?",
                "options": [
                    f"To optimize performance during execution",
                    f"To provide a standard way of organizing data",
                    f"To handle asynchronous operations effectively",
                    f"To ensure security and data integrity"
                ],
                "correct": random.randint(0, 3)
            },
            {
                "question": f"Which of the following is a key feature of {concept} in {cat} development?",
                "options": [
                    "High scalability and low latency",
                    "Strong type checking and validation",
                    "Ease of use and rapid prototyping",
                    "Extensive community support and documentation"
                ],
                "correct": random.randint(0, 3)
            },
            {
                "question": f"When implementing {concept} in a {cat} project, what is a common challenge?",
                "options": [
                    "Managing memory leaks and performance bottlenecks",
                    "Ensuring cross-platform compatibility",
                    "Integrating with third-party legacy systems",
                    "Scaling the infrastructure horizontally"
                ],
                "correct": random.randint(0, 3)
            }
        ]
        
        tpl = random.choice(templates)
        dataset.append({
            "id": len(dataset) + 1,
            "question": tpl["question"],
            "options": tpl["options"],
            "correct": tpl["correct"],
            "category": cat,
            "difficulty": diff
        })
        
    return dataset[:count]

MCQ_DATASET = generate_mcq_dataset(500)
